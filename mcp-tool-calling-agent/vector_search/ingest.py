"""
vector_search/ingest.py
-----------------------
Document ingestion pipeline.

Workflow:
    Text document
        ↓
    Chunking (split into overlapping paragraphs)
        ↓
    In-memory chunk store (DEMO_MODE)
        OR
    Databricks Vector Search index (production)

In DEMO_MODE=true:
    Chunks are stored in a Python list in memory.
    No embeddings or external services are used.
    This is clearly a LOCAL FALLBACK, not Databricks Vector Search.

In DEMO_MODE=false:
    Would push chunks to a Databricks Vector Search index.
    Requires DATABRICKS_VECTOR_SEARCH_ENDPOINT to be set.
    (Full implementation left for production setup with real credentials.)
"""

import logging
import os
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)

# ── In-memory chunk store for DEMO_MODE ──────────────────────────────────────
# Each item: {"doc_name": str, "chunk_id": int, "text": str}
_CHUNK_STORE: list[dict] = []
_INGESTED = False   # flag so we only ingest once per process


def _get_documents_dir() -> pathlib.Path:
    base = pathlib.Path(__file__).parent.parent
    return base / os.getenv("DOCUMENTS_DIR", "documents")


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    Split text into overlapping chunks by word count.

    Args:
        text: Full document text.
        chunk_size: Approximate words per chunk.
        overlap: Words to overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def ingest_documents(force: bool = False) -> int:
    """
    Load and chunk all policy documents into the in-memory store.

    This is the LOCAL DEMO fallback. It does NOT use Databricks Vector Search.

    Args:
        force: Re-ingest even if already done.

    Returns:
        Number of chunks created.
    """
    global _INGESTED, _CHUNK_STORE

    if _INGESTED and not force:
        return len(_CHUNK_STORE)

    _CHUNK_STORE.clear()
    docs_dir = _get_documents_dir()

    doc_files = {
        "company_policy": "company_policy.txt",
        "leave_policy":   "leave_policy.txt",
        "security_policy": "security_policy.txt",
    }

    for doc_name, filename in doc_files.items():
        filepath = docs_dir / filename
        if not filepath.exists():
            logger.warning("Document not found: %s", filepath)
            continue

        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            _CHUNK_STORE.append({
                "doc_name":  doc_name,
                "chunk_id":  i,
                "text":      chunk,
                "source":    filename,
            })

        logger.info("Ingested %d chunks from %s", len(chunks), filename)

    _INGESTED = True
    logger.info(
        "LOCAL DEMO ingestion complete. Total chunks: %d. "
        "(This is a local keyword store, NOT Databricks Vector Search.)",
        len(_CHUNK_STORE),
    )
    return len(_CHUNK_STORE)


def get_chunks() -> list[dict]:
    """Return the in-memory chunk store (ingesting if needed)."""
    if not _INGESTED:
        ingest_documents()
    return _CHUNK_STORE
