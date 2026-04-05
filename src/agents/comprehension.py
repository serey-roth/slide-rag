import base64
import io
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from src.learner_model import LearnerModel
from src.llm import call_anthropic
from src.prompts import TOPIC_EXTRACTION_PROMPT, TOPICS_CONSOLIDATION_PROMPT


IMAGES_DIR = Path("data/images")
BATCH_SIZE = 20


def _load_slides_as_jpeg(deck: str) -> list[str]:
    images_dir = IMAGES_DIR / deck
    if not images_dir.exists():
        raise RuntimeError(f"No images found for deck '{deck}'. Run ingest first.")
    result = []
    for path in sorted(images_dir.glob("*.png")):
        img = Image.open(path).convert("RGB")
        if img.width > 1024:
            ratio = 1024 / img.width
            img = img.resize((1024, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        result.append(base64.standard_b64encode(buf.getvalue()).decode())
    return result


def _extract_batch_topics(images: list[str]) -> list[str]:
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img}}
        for img in images
    ]
    content.append({"type": "text", "text": TOPIC_EXTRACTION_PROMPT})
    text = call_anthropic(messages=[{"role": "user", "content": content}], max_tokens=512)
    return [t.strip() for t in text.splitlines() if t.strip()]


def _consolidate(raw_topics: list[str]) -> tuple[str, list[str]]:
    raw_text = "\n".join(f"- {t}" for t in raw_topics)
    text = call_anthropic(
        messages=[{"role": "user", "content": TOPICS_CONSOLIDATION_PROMPT.format(raw=raw_text)}],
        max_tokens=512,
    )
    summary_m = re.search(r"^summary:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    summary = summary_m.group(1).strip() if summary_m else ""
    topics = [t.strip() for t in re.findall(r"^-\s*(.+)", text, re.MULTILINE)]
    return summary, topics


def comprehend(deck: str, learner_model: LearnerModel) -> tuple[str, list[str]]:
    """Extract topics and a summary from a deck's slides."""
    print(f"[comprehension] Loading slides for {deck}...")
    slides = _load_slides_as_jpeg(deck)
    total = len(slides)
    batches = [slides[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    print(f"[comprehension] Processing {total} slides in {len(batches)} batch(es) via Claude...")

    raw_topics: list[str] = []
    with ThreadPoolExecutor(max_workers=min(len(batches), 5)) as pool:
        futures = {pool.submit(_extract_batch_topics, batch): i for i, batch in enumerate(batches)}
        results = [None] * len(batches)
        for future in as_completed(futures):
            results[futures[future]] = future.result()
            print(f"[comprehension] {sum(r is not None for r in results)}/{len(batches)} batches done")
    for r in results:
        raw_topics.extend(r)

    if not raw_topics:
        print("[comprehension] No topics extracted.")
        return "", []

    print(f"[comprehension] Consolidating {len(raw_topics)} raw topics...")
    summary, topics = _consolidate(raw_topics)
    learner_model.add_deck(deck, summary, topics)
    print(f"[comprehension] Done — {len(topics)} topics → learner model updated")
    return summary, topics
