from __future__ import annotations
from datetime import time, date
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List

from .basic_structures import Duration
from .basic_types import Day
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# CALENDAR ENTITIES (from Calendar.rng)
# =============================================================================

class ShutdownPeriod(BaseModel):
    """A planned shutdown / betriebsferien period"""
    start_date: date = Field(..., description="Start date of the shutdown period")
    end_date: date = Field(..., description="End date of the shutdown period")
    description: Optional[str] = Field(None, description="Description of the shutdown")


class Break(IdentifiableEntity):
    """A break period within a shift"""
    start_time: time = Field(..., description="Break start time")
    end_time: time = Field(..., description="Break end time")


class Shift(IdentifiableEntity):
    """A single work shift definition"""
    day_of_week: Optional[Day] = Field(None, description="Day of week this shift applies to")
    start_time: time = Field(..., description="Shift start time")
    end_time: time = Field(..., description="Shift end time")
    breaks: List[Break] = Field(default_factory=list, description="Breaks within this shift")


class ShiftSchedule(IdentifiableEntity):
    """A schedule of shifts (collection of shifts forming a repeating pattern)"""
    shifts: List[Shift] = Field(default_factory=list, description="Shifts in this schedule")


class Holiday(IdentifiableEntity):
    """A holiday (non-working day)"""
    holiday_date: date = Field(..., description="Date of the holiday")


class AvailabilityException(IdentifiableEntity):
    """An exception to the normal availability schedule"""
    exception_date: date = Field(..., description="Date of the exception")
    available: bool = Field(..., description="Whether the resource is available on this date")
    start_time: Optional[time] = Field(None, description="Availability start time (if partially available)")
    end_time: Optional[time] = Field(None, description="Availability end time (if partially available)")

    @model_validator(mode='after')
    def check_partial_availability_times(self):
        if self.start_time is not None and self.end_time is None:
            raise ValueError("end_time must be specified when start_time is given")
        if self.end_time is not None and self.start_time is None:
            raise ValueError("start_time must be specified when end_time is given")
        return self


class Calendar(IdentifiableEntity):
    """Calendar definition grouping shifts, schedules, holidays, and exceptions"""
    shift_schedules: List[ShiftSchedule] = Field(default_factory=list, description="Shift schedules")
    shifts: List[Shift] = Field(default_factory=list, description="Individual shifts")
    holidays: List[Holiday] = Field(default_factory=list, description="Holidays")
    availability_exceptions: List[AvailabilityException] = Field(
        default_factory=list,
        description="Availability exceptions"
    )
    production_days_per_year: Optional[int] = Field(
        None, description="Number of production days per year (produktionstage_pro_jahr)"
    )
    shutdown_periods: List[ShutdownPeriod] = Field(
        default_factory=list, description="Planned shutdown / betriebsferien periods"
    )
