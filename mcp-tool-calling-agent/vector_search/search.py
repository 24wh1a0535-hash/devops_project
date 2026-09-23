"""
vector_search/search.py
-----------------------
Document search layer.

Architecture:
    Query
      ↓
    search_documents()
      ↓
    DEMO_MODE=true  → Local keyword + TF-IDF-style scoring (no embeddings)
    DEMO_MODE=false → Databricks Vector Search (semantic similarity)
      ↓
    Top-k relevant chunks
      ↓
    MCP tool (search_company_policy)
      ↓
    LangGraph Agent

IMPORTANT: The local fallback is keyword-based scoring.
It is clearly NOT Databricks Vector Search.
It is provided so the project can be demonstrated without cloud credentials.
"""

import logging
import math
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Stop-words filtered from query tokens ────────────────────────────────────
# Common English words that appear everywhere and dilute relevance scores.
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "what", "where", "when",
    "who", "which", "how", "why", "i", "me", "my", "we", "our", "you",
    "your", "it", "its", "they", "their", "them", "this", "that", "these",
    "those", "of", "in", "on", "at", "to", "for", "with", "about", "from",
    "by", "as", "or", "and", "not", "no", "all", "any", "some", "get",
    "give", "tell", "show", "find", "list", "please",
}

# ── Synonym / alias expansion ─────────────────────────────────────────────────
# Maps query words that do NOT appear in documents to words that DO.
# Covers natural-language phrasings that differ from policy document vocabulary.
_SYNONYMS: dict[str, list[str]] = {
    # "password requirements" → the section uses "password" + "policy" + "length"
    "requirements": ["policy", "rules", "length", "characters", "must"],
    "requirement":  ["policy", "rule", "must"],
    "rules":        ["policy", "must", "prohibited", "required"],
    "rule":         ["policy", "must"],
    # leave / vacation synonyms
    "vacation":     ["leave", "annual", "days"],
    "holidays":     ["leave", "annual", "holiday"],
    "pto":          ["leave", "annual"],
    "time":         ["days", "hours", "leave"],
    # security synonyms
    "security":     ["security", "password", "access", "mfa", "encrypt"],
    "login":        ["password", "authentication", "mfa"],
    "credentials":  ["password", "authentication"],
    "2fa":          ["mfa", "authentication", "factor"],
    "twofactor":    ["mfa", "authentication"],
    # general
    "info":         ["information", "details"],
    "details":      ["information", "description"],
    "policies":     ["policy"],
}


# ── Local keyword search (DEMO_MODE) ─────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split into tokens."""
    return re.findall(r"[a-z]+", text.lower())


def _expand_query_tokens(tokens: list[str]) -> list[str]:
    """
    Remove stop-words and expand synonyms so natural-language queries
    match policy document vocabulary.

    E.g. ["what", "are", "the", "password", "requirements"]
         → ["password", "policy", "rules", "length", "characters", "must"]
    """
    expanded: list[str] = []
    for token in tokens:
        if token in _STOP_WORDS:
            continue  # drop stop-words entirely
        if token in _SYNONYMS:
            expanded.extend(_SYNONYMS[token])  # replace with document vocabulary
        else:
            expanded.append(token)  # keep as-is
    return expanded


def _score_chunk(chunk_text: str, query_tokens: list[str]) -> float:
    """
    TF-based relevance score after stop-word removal and synonym expansion.
    Counts how many expanded query tokens appear in the chunk.
    """
    chunk_tokens = _tokenize(chunk_text)
    total = len(chunk_tokens) or 1
    score = 0.0
    for token in query_tokens:
        count = chunk_tokens.count(token)
        if count > 0:
            score += (count / total) * (1 + math.log(count))
    return score


def _local_search(query: str, doc_filter: Optional[str], top_k: int) -> list[dict]:
    """
    Keyword search over the in-memory chunk store.
    This is the LOCAL DEMO fallback — NOT Databricks Vector Search.

    Query tokens are stop-word filtered and synonym-expanded so that
    natural-language queries (e.g. "password requirements") correctly
    match policy document vocabulary (e.g. "PASSWORD POLICY … length …").
    """
    from vector_search.ingest import get_chunks

    chunks = get_chunks()
    if doc_filter:
        chunks = [c for c in chunks if c["doc_name"] == doc_filter]

    raw_tokens = _tokenize(query)
    query_tokens = _expand_query_tokens(raw_tokens)
    if not query_tokens:
        return []

    scored = []
    for chunk in chunks:
        score = _score_chunk(chunk["text"], query_tokens)
        if score > 0:
            scored.append({**chunk, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def _databricks_vector_search(
    query: str, doc_filter: Optional[str], top_k: int
) -> list[dict]:
    """
    Databricks Vector Search retrieval (production mode).

    Requires:
        DATABRICKS_VECTOR_SEARCH_ENDPOINT   endpoint name
        DATABRICKS_CATALOG, DATABRICKS_SCHEMA  for index name

    NOTE: Full production implementation requires:
        - A Delta table with document chunks
        - A Vector Search index created via Databricks UI or SDK
        - The databricks-vectorsearch SDK installed

    This stub shows the integration pattern.
    """
    endpoint = os.getenv("DATABRICKS_VECTOR_SEARCH_ENDPOINT", "")
    catalog   = os.getenv("DATABRICKS_CATALOG", "main")
    schema    = os.getenv("DATABRICKS_SCHEMA", "acme_company")

    if not endpoint:
        raise ValueError(
            "DATABRICKS_VECTOR_SEARCH_ENDPOINT is not set. "
            "Set it in .env or use DEMO_MODE=true."
        )

    try:
        from databricks.vector_search.client import VectorSearchClient  # type: ignore

        client = VectorSearchClient()
        index_name = f"{catalog}.{schema}.policy_docs_index"
        index = client.get_index(
            endpoint_name=endpoint,
            index_name=index_name,
        )

        filters = {"doc_name": doc_filter} if doc_filter else {}
        results = index.similarity_search(
            query_text=query,
            columns=["doc_name", "chunk_id", "text", "source"],
            num_results=top_k,
            filters=filters if filters else None,
        )

        hits = results.get("result", {}).get("data_array", [])
        columns = results.get("manifest", {}).get("columns", [])
        col_names = [c["name"] for c in columns]

        return [
            {**dict(zip(col_names, hit)), "score": hit[-1]}
            for hit in hits
        ]

    except ImportError:
        raise ImportError(
            "databricks-vectorsearch is not installed. "
            "Run: pip install databricks-vectorsearch"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def search_documents(
    query: str,
    doc_filter: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    """
    Search policy documents and return relevant chunks.

    In DEMO_MODE=true:  Uses local keyword scoring (no cloud needed).
    In DEMO_MODE=false: Uses Databricks Vector Search (requires credentials).

    Args:
        query:      The search question or keywords.
        doc_filter: Optional doc name filter: 'company_policy',
                    'leave_policy', or 'security_policy'.
        top_k:      Maximum number of results to return.

    Returns:
        dict with keys:
            mode:     'local_keyword_search' or 'databricks_vector_search'
            query:    The original query
            results:  List of matching chunks with scores
            count:    Number of results
    """
    if not query or not query.strip():
        return {"error": "query cannot be empty", "results": [], "count": 0}

    query = query.strip()
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    valid_docs = {"company_policy", "leave_policy", "security_policy"}
    if doc_filter and doc_filter not in valid_docs:
        return {
            "error": f"Unknown document '{doc_filter}'. Choose from: {sorted(valid_docs)}",
            "results": [],
            "count": 0,
        }

    if demo_mode:
        logger.debug("Using LOCAL keyword search (DEMO_MODE=true)")
        results = _local_search(query, doc_filter, top_k)
        mode = "local_keyword_search"
    else:
        logger.debug("Using Databricks Vector Search (DEMO_MODE=false)")
        try:
            results = _databricks_vector_search(query, doc_filter, top_k)
            mode = "databricks_vector_search"
        except Exception as e:
            logger.error("Databricks Vector Search failed: %s. Falling back to local.", e)
            results = _local_search(query, doc_filter, top_k)
            mode = f"local_keyword_search_fallback (Databricks error: {e})"

    return {
        "mode":    mode,
        "query":   query,
        "results": results,
        "count":   len(results),
    }
