"""
ingest.py — Parse a PDF slide deck and store chunks in Chroma + BM25.

Pipeline:
    Stage 1  parse_deck()          PDF → cleaned slide dicts (no API calls)
    Stage 2  create_embeddings()   slide text → embedding vectors
    Stage 3  store_embeddings()    embedding vectors → Chroma
    Stage 4  build_bm25_index()    slide text → bm25_index/

Usage:
    python ingest.py data/decks/week1.pdf --parse-only   # test parsing, no API calls
    python ingest.py data/decks/week1.pdf                # full ingest
    python ingest.py data/decks/week1.pdf --force        # clear and rebuild
"""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
import pymupdf4llm

from config import CHROMA_DIR, EMBEDDING_MODEL, BM25_DIR

# ---------------------------------------------------------------------------
# Parse slide deck in PDF
# ---------------------------------------------------------------------------
def _extract_page_text(markdown: str) -> tuple[str, str]:
    """
    Extract (title, body) from a pymupdf4llm page markdown chunk.

    Future work: for slides that are primarily images (e.g. diagrams, charts), consider
    running OCR or a vision model to recover the image content rather than dropping it.
    """
    
    # Matches footers like "3 / 35", "3/35", "Slide 3 of 35"
    _PAGE_FOOTER_RE = re.compile(r"^\d+\s*/\s*\d+$|^slide\s+\d+\s+of\s+\d+$", re.IGNORECASE)
    # Matches pymupdf4llm picture placeholders like "==> picture [681 x 60] intentionally omitted <=="
    _PICTURE_RE = re.compile(r"==> picture \[.*?\] intentionally omitted <==")
    # Matches pymupdf4llm picture text blocks — typically just source URLs, not useful content
    _PICTURE_TEXT_RE = re.compile(r"----- Start of picture text -----.*?----- End of picture text -----", re.DOTALL)
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")

    markdown = _PICTURE_TEXT_RE.sub("", markdown)
    lines = markdown.splitlines()

    ## - Picture placeholder lines ("==> picture [...] intentionally omitted <==") are removed.
    ## - Picture text blocks ("Start/End of picture text") are removed — these are typically
    ##  just source URLs captured from image captions, not slide content.
    ## - Footer lines (e.g. "3 / 35") are removed.
    lines = [l for l in lines if not _PAGE_FOOTER_RE.match(l.strip()) and not _PICTURE_RE.search(l)]

    # Find the first heading of any level as the title, preferring #
    title = ""
    body_lines = []
    found_title = False
    for line in lines:
        if not found_title:
            m = _HEADING_RE.match(line)
            if m:
                title = m.group(2).strip()
                found_title = True
                continue
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body


def _build_document(title: str, body: str) -> str:
    parts = []
    if title:
        parts.append(title)
    if body:
        parts.append(body)
    return "\n\n".join(parts)


def _content_hash(document: str) -> str:
    return "sha256:" + hashlib.sha256(document.encode()).hexdigest()


def parse_deck(pdf_path: str) -> list[dict]:
    """
    Parse a PDF into a list of slide dicts.

    Slides with fewer than MIN_TOKENS tokens are dropped (typically title-only or
    image-only slides with no recoverable text).

    Each slide dict contains:
        slide_number, title, body, document,
        token_count, content_hash,
        prev_slide_text, next_slide_text

    prev/next_slide_text provides adjacent-slide context for retrieval — useful
    when a concept spans multiple slides.

    Future work: support multi-PDF ingestion in a single pass; detect and tag
    slide types (title slide, agenda, diagram-heavy) for query-time filtering.
    """
    slides = []
    
    import tiktoken
    _tokenizer = tiktoken.get_encoding("cl100k_base")

    chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, show_progress=False)
    print(f"  {len(chunks)} pages found")
    for chunk in chunks:
        page_num = chunk["metadata"]["page_number"]  # 1-based
        title, body = _extract_page_text(chunk["text"])
        document = _build_document(title, body)
        token_count = len(_tokenizer.encode(document))

        MIN_TOKENS = 20;
        if token_count < MIN_TOKENS:
            continue

        slides.append({
            "slide_number": page_num,
            "title": title,
            "body": body,
            "document": document,
            "token_count": token_count,
            "content_hash": _content_hash(document),
            "prev_slide_text": "",
            "next_slide_text": "",
        })

    skipped = len(chunks) - len(slides)
    print(f"  {len(slides)} slides kept  ({skipped} skipped, < {MIN_TOKENS} tokens)")

    # Attach adjacent context
    for j, s in enumerate(slides):
        s["prev_slide_text"] = slides[j - 1]["document"] if j > 0 else ""
        s["next_slide_text"] = slides[j + 1]["document"] if j < len(slides) - 1 else ""

    return slides


# ---------------------------------------------------------------------------
# Embed and store in Chroma
# ---------------------------------------------------------------------------
def create_embeddings(slides: list[dict], deck_name: str, batch_size: int = 100) -> tuple[list[dict], list[list[float]]]:
    """
    Compute embeddings for each slide document.

    Returns (slides, embeddings) — both lists are in the same order and ready
    to pass directly to store_embeddings().
    """
    from sentence_transformers import SentenceTransformer

    def _embed_text(s: dict) -> str:
        parts = [f"Deck: {deck_name}", s["document"]]
        if s["prev_slide_text"]:
            parts.insert(1, f"Previous slide: {s['prev_slide_text']}")
        if s["next_slide_text"]:
            parts.append(f"Next slide: {s['next_slide_text']}")
        return "\n\n".join(parts)

    model = SentenceTransformer(EMBEDDING_MODEL)
    n_batches = (len(slides) + batch_size - 1) // batch_size
    print(f"  Embedding {len(slides)} slides  ({n_batches} batch(es))")

    all_embeddings = []
    for i in range(0, len(slides), batch_size):
        batch_num = i // batch_size + 1
        print(f"  batch {batch_num}/{n_batches}...", end="\r", flush=True)
        batch = [_embed_text(s) for s in slides[i : i + batch_size]]
        all_embeddings.extend(model.encode(batch, normalize_embeddings=True).tolist())
    print()

    return slides, all_embeddings


def store_embeddings(
    slides: list[dict],
    embeddings: list[list[float]],
    deck_name: str,
    file_path: str,
    force: bool = False,
) -> int:
    """
    Upsert slide embeddings into Chroma, skipping unchanged slides.

    Deduplication is by content_hash — slides already in Chroma with the same
    hash are skipped unless --force is passed.

    Returns the number of slides newly stored.
    """
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name="slides",
        metadata={"hnsw:space": "cosine"},
    )

    if force:
        existing = collection.get(where={"deck_name": deck_name})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"  [--force] Deleted {len(existing['ids'])} existing chunks.")

    existing_hashes: set[str] = set()
    if not force:
        existing = collection.get(where={"deck_name": deck_name}, include=["metadatas"])
        for meta in existing["metadatas"]:
            existing_hashes.add(meta.get("content_hash", ""))

    pairs = [(s, e) for s, e in zip(slides, embeddings) if s["content_hash"] not in existing_hashes]
    skipped = len(slides) - len(pairs)

    if not pairs:
        print(f"  Nothing to store ({skipped} slides already up to date).")
        return 0

    to_store, to_embed = zip(*pairs)
    print(f"  Storing {len(to_store)} chunks  ({skipped} unchanged)")

    collection.upsert(
        ids=[f"{deck_name}__slide_{s['slide_number']:03d}" for s in to_store],
        documents=[s["document"] for s in to_store],
        embeddings=list(to_embed),
        metadatas=[
            {
                "deck_name": deck_name,
                "file_path": file_path,
                "slide_number": s["slide_number"],
                "title": s["title"],
                "token_count": s["token_count"],
                "content_hash": s["content_hash"],
                "prev_slide_text": s["prev_slide_text"][:1000],
                "next_slide_text": s["next_slide_text"][:1000],
            }
            for s in to_store
        ],
    )
    print(f"  Stored {len(to_store)} chunks in Chroma.")
    return len(to_store)


# ---------------------------------------------------------------------------
# Stage 3: Build BM25 index
# ---------------------------------------------------------------------------
def build_bm25_index(slides: list[dict], deck_name: str) -> None:
    """
    Build and persist a bm25s index over all ingested decks.

    Layout:
        bm25_index/corpus.json      — {deck_name: [{id, text}]} for deck filtering
        bm25_index/index/           — bm25s binary index (pre-tokenized)
        bm25_index/index/ids.json   — ordered list of slide IDs (maps index pos → id)

    The corpus entry for this deck is overwritten; the combined index is rebuilt
    over all decks so IDF scores reflect the full corpus.
    """
    import bm25s

    Path(BM25_DIR).mkdir(exist_ok=True)
    corpus_path = Path(BM25_DIR) / "corpus.json"
    index_dir = Path(BM25_DIR) / "index"

    corpus: dict = {}
    if corpus_path.exists():
        with open(corpus_path) as f:
            corpus = json.load(f)

    corpus[deck_name] = [
        {"id": f"{deck_name}__slide_{s['slide_number']:03d}", "text": s["document"]}
        for s in slides
    ]
    with open(corpus_path, "w") as f:
        json.dump(corpus, f)

    all_entries = [e for entries in corpus.values() for e in entries]
    print(f"  Tokenizing {len(all_entries)} slides...")
    tokenized = bm25s.tokenize([e["text"] for e in all_entries])
    index = bm25s.BM25()
    index.index(tokenized)
    index.save(str(index_dir))

    with open(index_dir / "ids.json", "w") as f:
        json.dump([e["id"] for e in all_entries], f)

    print(f"  BM25 index built ({len(all_entries)} slides across {len(corpus)} deck(s)).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def ingest(pdf_path: str, force: bool = False) -> None:
    t0 = time.time()
    
    path = Path(pdf_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    deck_name = path.stem

    print(f"[ingest] {deck_name}  {'(force rebuild)' if force else ''}")

    print("[1/4] Parsing PDF...")
    slides = parse_deck(pdf_path)
    print(f"      done {len(slides)} slides  ({time.time() - t0:.1f}s)")

    print("[2/4] Creating embeddings...")
    slides, embeddings = create_embeddings(slides, deck_name)
    print(f"      done  ({time.time() - t0:.1f}s)")

    print("[3/4] Storing embeddings in Chroma...")
    store_embeddings(slides, embeddings, deck_name, str(path), force=force)
    print(f"      done  ({time.time() - t0:.1f}s)")

    print("[4/4] Building BM25 index...")
    build_bm25_index(slides, deck_name)
    print(f"      done  ({time.time() - t0:.1f}s)")


    print(f"[ingest] finished in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest a PDF slide deck into the slide RAG index."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear and rebuild the Chroma index for this deck",
    )
    args = parser.parse_args()
    ingest(args.pdf_path, force=args.force)
