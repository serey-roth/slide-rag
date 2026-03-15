"""
retrieve.py — Hybrid retrieval for slide RAG.

Pipeline per query:
    1. Embed query → Chroma vector search → top-10 candidates
    2. BM25 keyword search (bm25s, pre-tokenized) → top-10 candidates
    3. Reciprocal Rank Fusion (RRF) → top-8 slides, deduped by content_hash

Indices are loaded once at module level. Progress is logged to stderr.
Used by app.py for answer generation.
"""

import json
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import bm25s
import chromadb
from sentence_transformers import SentenceTransformer

from src.config import CHROMA_DIR, EMBEDDING_MODEL, BM25_DIR

# ---------------------------------------------------------------------------
# Load indices (done once at module level so CLI reuse is fast)
# ---------------------------------------------------------------------------
_embed_model = SentenceTransformer(EMBEDDING_MODEL)
_chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _chroma_client.get_collection("slides")

# Load bm25s index and corpus once at startup
_bm25_index = bm25s.BM25.load(str(Path(BM25_DIR) / "index"))
with open(Path(BM25_DIR) / "index" / "ids.json") as _f:
    _bm25_ids: list[str] = json.load(_f)
with open(Path(BM25_DIR) / "corpus.json") as _f:
    _bm25_corpus: dict = json.load(_f)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def _vector_search(query: str, deck_filter: str | list[str] | None, top_k: int) -> list[dict]:
    """
    Embed the query and search Chroma for the nearest neighbours.

    Returns a list of Chroma result dicts with keys: id, document, metadata.
    """
    embedding = _embed_model.encode(query, normalize_embeddings=True).tolist()
    
    if deck_filter is None:
        where = None
    elif isinstance(deck_filter, str):
        where = {"deck_name": deck_filter}
    else:
        where = {"deck_name": {"$in": deck_filter}}
        
    results = _collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas"],
    )
    
    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        hits.append({
            "id": doc_id,
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        })
    return hits


def _bm25_search(query: str, deck_filter: str | list[str] | None, top_k: int) -> list[dict]:
    """
    Search the bm25s index and return the top-k hits as {id} dicts.

    No deck filter: use the pre-built global index (fast, no re-tokenization).
    With deck filter: build a small temporary index from the filtered corpus
    so IDF scores are correct for the restricted set.
    """
    query_tokens = bm25s.tokenize([query])

    if deck_filter is None:
        results, _ = _bm25_index.retrieve(query_tokens, k=min(top_k, len(_bm25_ids)))
        return [{"id": _bm25_ids[i]} for i in results[0]]

    allowed = {deck_filter} if isinstance(deck_filter, str) else set(deck_filter)
    filtered = [e for dk, entries in _bm25_corpus.items() if dk in allowed for e in entries]
    if not filtered:
        return []
    
    tmp = bm25s.BM25()
    tmp.index(bm25s.tokenize([e["text"] for e in filtered]))
    
    results, _ = tmp.retrieve(query_tokens, k=min(top_k, len(filtered)))
    return [{"id": filtered[i]["id"]} for i in results[0]]


def _rrf(vector_hits: list[dict], bm25_hits: list[dict], top_n: int) -> list[str]:
    """
    Reciprocal Rank Fusion: merge two ranked lists into a single ranking.

    RRF score for a document = sum over each list of 1 / (k + rank).
    k=60 is the standard default; it dampens the influence of very high ranks.

    Returns a list of document IDs in fused rank order, length top_n.
    """
    scores: dict[str, float] = {}
    RRF_K = 60    

    for rank, hit in enumerate(vector_hits, start=1):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (RRF_K + rank)

    for rank, hit in enumerate(bm25_hits, start=1):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (RRF_K + rank)

    ranked = sorted(scores, key=lambda d: scores[d], reverse=True)
    return ranked[:top_n]


def build_context(slides: list[dict]) -> str:
    """
    Format retrieved slides into a context for the answer prompt.

    Each slide includes its number, title, content, and adjacent slide text
    for continuity. Sparse slides are passed as-is — Claude is instructed in
    the system prompt to supplement them with its own knowledge inline.
    """
    blocks = []
    for slide in slides:
        meta = slide["metadata"]
        slide_num = meta["slide_number"]
        title = meta.get("title", "")
        prev_text = meta.get("prev_slide_text", "")
        next_text = meta.get("next_slide_text", "")

        deck_name = meta.get("deck_name", "")
        parts = [f"[{deck_name}, Slide {slide_num}]" if deck_name else f"[Slide {slide_num}]"]
        if title:
            parts.append(f"Title: {title}")
        parts.append(f"Content: {slide['document']}")
        if prev_text:
            parts.append(f"Previous slide: {prev_text}")
        if next_text:
            parts.append(f"Next slide: {next_text}")

        blocks.append("\n".join(parts))

    return "\n\n---\n\n".join(blocks)


# TODO: Add topK to param
def retrieve(query: str, deck_filter: str | list[str] | None = None) -> list[dict]:
    """
    Run hybrid retrieval for a query and return the top-N slide dicts.

    Each returned dict has: id, document, metadata (deck_name, slide_number,
    title, token_count, prev_slide_text, next_slide_text).

    Future work: add a cross-encoder re-ranker as a post-fusion step for
    higher precision (deferred per PRD — V2).
    """
    VECTOR_TOP_K = 10       # candidates from Chroma
    BM25_TOP_K = 10         # candidates from BM25
    RRF_TOP_N = 8          # final slides after fusion

    print(f"[retrieve] retrieve relevant slides for query: " + query[:60])
    t0 = time.time()

    print(f"[1/3] vector search...")
    vector_hits = _vector_search(query, deck_filter, VECTOR_TOP_K)
    print(f"      done (vector: {len(vector_hits)} hits)  ({time.time() - t0:.1f}s)")
    
    print(f"[2/3] bm25 search...")
    bm25_hits = _bm25_search(query, deck_filter, BM25_TOP_K)
    print(f"      done (bm25: {len(bm25_hits)} hits)  ({time.time() - t0:.1f}s)")

    print(f"[3/4] rrf...")
    top_ids = _rrf(vector_hits, bm25_hits, RRF_TOP_N)
    print(f"      done  ({time.time() - t0:.1f}s)")

    # Build an id→hit map from vector results (already have full metadata)
    id_to_hit = {h["id"]: h for h in vector_hits}

    # For any IDs only found via BM25, fetch from Chroma
    missing = [doc_id for doc_id in top_ids if doc_id not in id_to_hit]
    if missing:
        fetched = _collection.get(ids=missing, include=["documents", "metadatas"])
        for i, doc_id in enumerate(fetched["ids"]):
            id_to_hit[doc_id] = {
                "id": doc_id,
                "document": fetched["documents"][i],
                "metadata": fetched["metadatas"][i],
            }

    slides = [id_to_hit[doc_id] for doc_id in top_ids if doc_id in id_to_hit]

    # Dedup across decks: if two slides share a content_hash, keep only the
    # highest-ranked one (already sorted by RRF score via top_ids order).
    seen_hashes: set[str] = set()
    unique_slides: list[dict] = []
    for slide in slides:
        h = slide["metadata"].get("content_hash", slide["id"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_slides.append(slide)

    slide_ids = "  ".join(s["id"] for s in unique_slides)
    print(f"      done  {len(unique_slides)} slides  ({time.time() - t0:.2f}s)  {slide_ids}")

    return unique_slides
