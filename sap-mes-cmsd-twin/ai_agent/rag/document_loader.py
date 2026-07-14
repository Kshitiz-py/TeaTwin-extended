"""
Document Loader — Reads, chunks, and prepares documents for embedding.
Supports Markdown, Python, TypeScript, JSON, and SQL files.
"""

import os
import re
import logging
from typing import List, Dict, Any

from ..config import CHUNK_SIZE, CHUNK_OVERLAP, DOC_SOURCES

logger = logging.getLogger("ai-agent.document-loader")


class DocumentChunk:
    """A single chunk of a document, ready for embedding."""

    def __init__(
        self,
        content: str,
        metadata: dict[str, Any],
        chunk_index: int,
    ):
        self.content = content
        self.metadata = metadata
        self.chunk_index = chunk_index


class DocumentLoader:
    """Loads documents from multiple sources and splits into chunks."""

    def load_all(self) -> list[DocumentChunk]:
        """Load all configured document sources and return chunked documents."""
        all_chunks: list[DocumentChunk] = []
        for source in DOC_SOURCES:
            path = source["path"]
            if not os.path.exists(path):
                logger.warning(f"Document source not found: {path}")
                continue

            chunks = self._load_source(source)
            all_chunks.extend(chunks)
            logger.info(f"Loaded {len(chunks)} chunks from {source['description']} ({path})")

        logger.info(f"Total document chunks loaded: {len(all_chunks)}")
        return all_chunks

    def _load_source(self, source: dict) -> list[DocumentChunk]:
        """Load a single source based on its type."""
        source_type = source["type"]
        path = source["path"]
        collection = source["collection"]
        description = source["description"]

        if source_type == "markdown":
            return self._load_markdown(path, collection, description)
        elif source_type == "code":
            return self._load_code_file(path, collection, description)
        elif source_type == "code_directory":
            return self._load_code_directory(path, collection, description)
        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    def _load_markdown(self, path: str, collection: str, description: str) -> list[DocumentChunk]:
        """Load a markdown file, splitting on headers."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split on ## headers for topic-based chunks
        sections = re.split(r"\n(?=## )", content)
        chunks = []
        for i, section in enumerate(sections):
            if section.strip():
                # Extract header for metadata
                header_match = re.match(r"^#{1,4}\s+(.+)", section.strip())
                header = header_match.group(1) if header_match else f"Section {i}"

                chunks.append(
                    DocumentChunk(
                        content=section.strip(),
                        metadata={
                            "source": path,
                            "collection": collection,
                            "description": description,
                            "header": header,
                            "type": "markdown",
                        },
                        chunk_index=i,
                    )
                )

        return chunks

    def _load_code_file(self, path: str, collection: str, description: str) -> list[DocumentChunk]:
        """Load a single code file, splitting on function/class boundaries."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # For code files, chunk by function/class definitions or by size
        filename = os.path.basename(path)

        # Try to split on def/class boundaries
        sections = re.split(r"\n(?=def |class |async def )", content)
        chunks = []
        current_chunk = ""
        chunk_idx = 0

        for section in sections:
            if len(current_chunk) + len(section) > CHUNK_SIZE and current_chunk:
                chunks.append(
                    DocumentChunk(
                        content=current_chunk.strip(),
                        metadata={
                            "source": path,
                            "filename": filename,
                            "collection": collection,
                            "description": description,
                            "type": "code",
                        },
                        chunk_index=chunk_idx,
                    )
                )
                chunk_idx += 1
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section

        if current_chunk.strip():
            chunks.append(
                DocumentChunk(
                    content=current_chunk.strip(),
                    metadata={
                        "source": path,
                        "filename": filename,
                        "collection": collection,
                        "description": description,
                        "type": "code",
                    },
                    chunk_index=chunk_idx,
                )
            )

        return chunks

    def _load_code_directory(self, path: str, collection: str, description: str) -> list[DocumentChunk]:
        """Load all code files from a directory recursively."""
        all_chunks: list[DocumentChunk] = []
        suffix_map = {
            ".py": "python",
            ".tsx": "typescript-react",
            ".ts": "typescript",
            ".sql": "sql",
            ".json": "json",
        }

        for root, dirs, files in os.walk(path):
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in suffix_map:
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Simple size-based chunking for directory files
                    chunks = self._chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
                    for i, chunk_text in enumerate(chunks):
                        all_chunks.append(
                            DocumentChunk(
                                content=chunk_text,
                                metadata={
                                    "source": file_path,
                                    "filename": file,
                                    "collection": collection,
                                    "description": description,
                                    "type": suffix_map[ext],
                                },
                                chunk_index=i,
                            )
                        )

        return all_chunks

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks by newlines, respecting chunk size."""
        lines = text.split("\n")
        chunks = []
        current_chunk: list[str] = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1  # +1 for newline
            if current_len + line_len > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                # Keep last few lines for overlap
                overlap_lines = []
                overlap_len = 0
                for ol in reversed(current_chunk):
                    if overlap_len + len(ol) > overlap:
                        break
                    overlap_lines.insert(0, ol)
                    overlap_len += len(ol) + 1
                current_chunk = overlap_lines
                current_len = overlap_len

            current_chunk.append(line)
            current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks


# Singleton
document_loader = DocumentLoader()