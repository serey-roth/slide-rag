import difflib
import requests
import numpy as np

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
SIMILARITY_THRESHOLD = 0.5
MULTI_TOPIC_THRESHOLD = 0.65  


_embed_cache: dict[str, np.ndarray] = {}


def _embed(text: str) -> np.ndarray:
    if text in _embed_cache:
        return _embed_cache[text]
    response = requests.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text})
    response.raise_for_status()
    vec = np.array(response.json()["embedding"], dtype=np.float32)
    _embed_cache[text] = vec
    return vec


def _calculate_cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def _find_text_match(question: str, topics: list[str]) -> str | None:
    q = question.lower()

    for t in topics:
        if t.lower() in q:
            return t

    matches = difflib.get_close_matches(q, [t.lower() for t in topics], n=1, cutoff=0.6)
    if matches:
        for t in topics:
            if t.lower() == matches[0]:
                return t

    return None


def resolve_topics(question: str, topics: list[str]) -> list[str]:
    """Return all topics relevant to the question."""
    if not topics:
        return []
    
    text_match = _find_text_match(question, topics)

    try:
        q_vec = _embed(question)
        scores = sorted(
            [(t, _calculate_cosine_similarity(q_vec, _embed(t))) for t in topics],
            key=lambda x: x[1],
            reverse=True,
        )
        print(f"[resolver] top matches: {[(t[:30], f'{s:.3f}') for t, s in scores[:3]]}")

        matched = [t for t, s in scores if s >= MULTI_TOPIC_THRESHOLD]

        # Always include the best match if it clears the lower threshold
        if not matched and scores[0][1] >= SIMILARITY_THRESHOLD:
            matched = [scores[0][0]]

        if text_match and text_match not in matched:
            matched.insert(0, text_match)

        return matched

    except Exception as e:
        print(f"[resolver] embedding match failed: {e}")
        return [text_match] if text_match else []


if __name__ == "__main__":
    topics = [
        "data science vs. decision science vs. business analytics distinctions",
        "iterative data science process workflow",
        "population vs. sample and representative random sampling",
        "sampling bias and data collection methods",
        "statistical thinking and sources of variability",
        "types of data questions (descriptive, exploratory, inferential, predictive, causal)",
        "question formulation technique for problem framing",
        "communicating results and literate programming with Jupyter",
        "divergent thinking, convergent thinking, and metacognition as learning skills",
        "course logistics and assessment structure",
    ]

    questions = [
        "what is the data science lifecycle",
        "how does EDA relate to problem framing?",
        "what are the types of data questions",
        "what's on the final exam?",
    ]

    for q in questions:
        result = resolve_topics(q, topics)
        print(f"Q: {q}\n→ {result}\n")
