from typing import Callable

from src.llm import call_anthropic_stream
from src.prompts import CHAT_PROMPT
from src.retrieve import build_context, retrieve


def _build_messages(history: list[dict], context: list[dict], query: str, learner_context: str | None) -> list[dict]:
    messages = list(history)

    user_content = []

    if learner_context:
        user_content.append({"type": "text", "text": f"Student learning context:\n{learner_context}"})

    for block in context:
        if block.get("type") == "image":
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": block["source"]["data"]},
            })
        elif block.get("type") == "text":
            user_content.append({"type": "text", "text": block["text"]})

    user_content.append({"type": "text", "text": f"Question: {query}"})
    messages.append({"role": "user", "content": user_content})
    return messages


def _build_learner_context(learner_model) -> str | None:
    lines = []
    for deck, data in learner_model._data.items():
        topics = data.get("topics", {})
        if not topics:
            continue
        lines.append(f"Deck: {deck}")
        for name, t in topics.items():
            progress = t.get("progress") or "not yet studied"
            lines.append(f"  - {name}: {progress}")
    return "\n".join(lines) if lines else None


def ask_question(
    query: str,
    history: list[dict],
    on_stream: Callable[[str], None] | None = None,
    learner_model=None,
) -> tuple[str, list[dict]]:
    """Ask a question about the slides."""
    slides = retrieve(queries=[query])
    slide_context = build_context(slides)
    learner_context = _build_learner_context(learner_model) if learner_model else None
    messages = _build_messages(history, slide_context, query, learner_context)
    response = call_anthropic_stream(
        messages=messages,
        system=CHAT_PROMPT,
        max_tokens=1024,
        on_token=on_stream,
    )
    return response, slides
