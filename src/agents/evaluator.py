import re

from src.llm import call_ollama
from src.prompts import EVALUATOR_PROMPT, QUIZ_EVALUATOR_PROMPT
from src.agents.resolver import resolve_topics


def evaluate(question: str, topic: str, existing_progress: str | None = None) -> str | None:
    """Returns a progress note string, or None if off-topic."""
    prior = f"Existing progress note: {existing_progress}" if existing_progress else "Existing progress note: none"
    prompt = (
        f"Topic: {topic}\n\n"
        f"{prior}\n\n"
        f"Student question: {question}"
    )
    text = call_ollama(f"{EVALUATOR_PROMPT}\n\n{prompt}", num_predict=80)
    progress_m = re.search(r"^progress:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    progress = progress_m.group(1).strip() if progress_m else None
    if not progress or progress.lower() == "null":
        return None
    return progress


def update_learner_model(query: str, learner_model) -> None:
    """Update the learner model with the progress note based on the question."""
    all_topics = []
    deck_for_topic = {}
    for deck, data in learner_model._data.items():
        for name in data.get("topics", {}).keys():
            all_topics.append(name)
            deck_for_topic[name] = deck

    if not all_topics:
        return

    matched_topics = resolve_topics(query, all_topics)
    if not matched_topics:
        return

    for topic in matched_topics:
        deck = deck_for_topic.get(topic)
        if not deck:
            continue
        existing = (learner_model.get_topic(deck, topic) or {}).get("progress")
        progress = evaluate(query, topic, existing_progress=existing)
        if not progress:
            continue
        learner_model.update_progress(deck, topic, progress)
        print(f"[learner_model] updated '{topic}' in '{deck}': {progress}")


def evaluate_quiz_result(topic: str, quiz_items: list[tuple[str, bool]], existing_progress: str | None = None) -> str | None:
    """Returns a progress note string based on quiz Q&A results, or None if off-topic."""
    prior = f"Existing progress note: {existing_progress}" if existing_progress else "Existing progress note: none"
    items_text = "\n".join(f"- {'✓' if correct else '✗'} {q}" for q, correct in quiz_items)
    prompt = (
        f"Topic: {topic}\n\n"
        f"{prior}\n\n"
        f"Quiz questions:\n{items_text}"
    )
    text = call_ollama(f"{QUIZ_EVALUATOR_PROMPT}\n\n{prompt}", num_predict=80)
    progress_m = re.search(r"^progress:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    progress = progress_m.group(1).strip() if progress_m else None
    if not progress or progress.lower() == "null":
        return None
    return progress


def update_learner_model_from_quiz(quiz, results: list[dict], learner_model) -> None:
    """Update the learner model based on quiz results."""
    quiz_items = [(r['q'].prompt, r['correct']) for r in results]

    all_topics = []
    deck_for_topic = {}
    for deck, data in learner_model._data.items():
        for name in data.get("topics", {}).keys():
            all_topics.append(name)
            deck_for_topic[name] = deck

    if not all_topics:
        return

    matched_topics = resolve_topics(" ".join(quiz.topics), all_topics)
    if not matched_topics:
        return

    for topic in matched_topics:
        deck = deck_for_topic.get(topic)
        if not deck:
            continue
        existing = (learner_model.get_topic(deck, topic) or {}).get("progress")
        progress = evaluate_quiz_result(topic, quiz_items, existing_progress=existing)
        if not progress:
            continue
        learner_model.update_progress(deck, topic, progress)
        print(f"[learner_model] quiz updated '{topic}' in '{deck}': {progress}")


if __name__ == "__main__":
    topic = "iterative data science process workflow"
    exchanges = [
        ("what is the data science lifecycle", None),
        ("why does EDA loop back to problem framing?", "Asked for a basic definition of the lifecycle; no prior depth demonstrated."),
        ("when would you skip the modeling step entirely?", "Understands the stages and the iterative feedback between EDA and problem framing; hasn't probed edge cases yet."),
    ]

    for q, prior in exchanges:
        result = evaluate(q, topic, existing_progress=prior)
        print(f"Prior:  {prior}")
        print(f"Q:      {q}")
        print(f"→       {result}\n")
