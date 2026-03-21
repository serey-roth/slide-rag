import base64
import json
from pathlib import Path
import numpy as np

import torch

from src.model import load_model

INDEX_DIR = "data/indexes"


def embed_queries(queries: list[str], model, processor) -> torch.Tensor:
    print(f"[query] Embedding {len(queries)} query/queries...")
    with torch.inference_mode():
        batch_queries = processor.process_queries(queries).to(model.device)
        embeddings = model(**batch_queries)
    print(f"[query] Done")
    return embeddings


def load_index(deck_filter: list[str] | None, device) -> tuple[list, list]:
    index_dir = Path(INDEX_DIR)
    if not index_dir.exists():
        raise RuntimeError("No embeddings found! Please ingest files first")

    decks = [d for d in index_dir.iterdir() if d.is_dir()]
    if deck_filter:
        decks = [d for d in decks if d.name in deck_filter]

    all_embeddings = []
    all_metadata = []
    for deck_dir in decks:
        embeddings = torch.from_numpy(np.load(deck_dir / "patch_embeddings.npy")).to(device)
        with open(deck_dir / "slide_index.json") as f:
            metadata = json.load(f)
        for i, meta in enumerate(metadata):
            all_embeddings.append(embeddings[i])
            all_metadata.append({"deck": deck_dir.name, **meta})
        print(f"[index] Loaded {len(metadata)} slides from {deck_dir.name}")

    print(f"[index] Total: {len(all_metadata)} slides across {len(decks)} deck(s)")
    return all_embeddings, all_metadata


def rank(query_embeddings: torch.Tensor, all_embeddings: list, all_metadata: list, processor, top_k: int) -> list:
    if not all_embeddings:
        return []

    print(f"[rank] Scoring {len(all_metadata)} slides...")
    doc_embeddings = torch.stack(all_embeddings)
    scores = processor.score_multi_vector(query_embeddings, doc_embeddings)

    agg_scores = scores.max(dim=0).values
    top_indices = agg_scores.topk(min(top_k, len(all_metadata))).indices.tolist()
    results = [{"score": float(agg_scores[i]), **all_metadata[i]} for i in top_indices]
    print(f"[rank] Top {len(results)} results — best score: {results[0]['score']:.3f}")
    return results


def build_context(slides: list[dict]) -> list[dict]:
    blocks = []
    for slide in slides:
        image_data = base64.standard_b64encode(
            Path(slide["image_path"]).read_bytes()
        ).decode("utf-8")
        blocks.append({"type": "text", "text": f"[{slide['deck']}, Slide {slide['slide_num']}]"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}})
    return blocks


def retrieve(queries: list[str], deck_filter: list[str] | None = None, top_k: int = 5) -> list:
    model, processor = load_model()
    query_embeddings = embed_queries(queries, model, processor)
    all_embeddings, all_metadata = load_index(deck_filter, model.device)
    return rank(query_embeddings, all_embeddings, all_metadata, processor, top_k)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Retrieve slides using ColPali visual embeddings.")
    parser.add_argument("queries", nargs="+", help="One or more search queries")
    parser.add_argument("--decks", nargs="+", help="Filter to specific deck names", default=None)
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()

    results = retrieve(args.queries, deck_filter=args.decks, top_k=args.top_k)
    for r in results:
        print(f"[{r['score']:.3f}] {r['deck']} — slide {r['slide_num']} ({r['image_path']})")
