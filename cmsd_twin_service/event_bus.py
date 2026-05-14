"""
EventBus — In-memory pub/sub event bus with asyncio.Queue for each subscriber.
Also maintains a change log in the MySQL database for persistence.
"""

import asyncio
import logging
import sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import config as app_config
from .change_detector import ChangeEvent

logger = logging.getLogger("cmsd-twin.event-bus")

engine = create_engine(app_config.database.url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class EventBus:
    """In-memory pub/sub with database-persisted change log."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._events: list[dict] = []  # In-memory buffer of recent events
        self._max_buffer = 200

    def subscribe(self) -> asyncio.Queue:
        """Register a new subscriber. Returns an async queue that receives events."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, events: list[ChangeEvent], poll_cycle_id: str = ""):
        """Publish change events to all subscribers and persist to DB."""
        event_dicts = [e.to_dict() for e in events]

        # Persist to DB
        self._persist_to_db(event_dicts, poll_cycle_id)

        # Push to all subscriber queues
        for event_dict in event_dicts:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event_dict)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping event")

        # In-memory buffer
        self._events.extend(event_dicts)
        if len(self._events) > self._max_buffer:
            self._events = self._events[-self._max_buffer:]

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        return self._events[-limit:]

    def get_events_since(self, timestamp: str) -> list[dict]:
        return [e for e in self._events if e.get("timestamp", "") > timestamp]

    def _persist_to_db(self, event_dicts: list[dict], poll_cycle_id: str):
        try:
            session = SessionLocal()
            for ev in event_dicts:
                session.execute(
                    """
                    INSERT INTO change_events 
                    (entity_type, entity_identifier, entity_name, field_name, old_value, new_value, event_type, poll_cycle_id, detected_at)
                    VALUES (:entity_type, :entity_identifier, :entity_name, :field_name, :old_value, :new_value, :event_type, :poll_cycle_id, :detected_at)
                    """,
                    {
                        "entity_type": ev["entity_type"],
                        "entity_identifier": ev["entity_identifier"],
                        "entity_name": ev.get("entity_name", ""),
                        "field_name": ev["field_name"],
                        "old_value": ev.get("old_value"),
                        "new_value": ev.get("new_value"),
                        "event_type": ev["event_type"],
                        "poll_cycle_id": poll_cycle_id,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            session.commit()
        except Exception as e:
            logger.error(f"Failed to persist change events to DB: {e}")
        finally:
            session.close()