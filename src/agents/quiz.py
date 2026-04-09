import re
from dataclasses import dataclass

from src.llm import call_anthropic
from src.prompts import QUIZ_GENERATION_PROMPT
from src.retrieve import build_context, retrieve


DEFAULT_NUM_QUESTIONS = 5

@dataclass
class Question:
    prompt: str
    options: list[str]
    answer: int
    slides: list[dict]


@dataclass
class Quiz:
    topics: list[str]
    questions: list[Question]


def _parse_question(block: str):
    block = block.strip()
    if not block:
        return None

    question_m = re.search(r"^question:\s*(.+?)(?=\noptions:)", block, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    options_start = re.search(r"^options:", block, re.IGNORECASE | re.MULTILINE)
    answer_m = re.search(r"^answer:\s*(.+?)(?=\nsources:|$)", block, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    sources_start = re.search(r"^sources:", block, re.IGNORECASE | re.MULTILINE)

    options_block = block[options_start.end():answer_m.start()] if options_start and answer_m else ""
    options = [o.strip() for o in re.findall(r"^-\s*(.+)", options_block, re.MULTILINE)]

    sources_block = block[sources_start.end():] if sources_start else ""
    sources = re.findall(r"\[([^\]]+)\]", sources_block)

    answer = answer_m.group(1).strip() if answer_m else None
    answer_index = next((i for i, o in enumerate(options) if o == answer), None)

    if not question_m or not options or answer_index is None:
        return None

    return Question(
        prompt=question_m.group(1).strip(),
        options=options,
        answer=answer_index,
        slides=[],
    ), sources


def _build_learner_context(topics: list[str], learner_model) -> str:
    if learner_model is None:
        return ""
    from src.agents.resolver import resolve_topics
    all_topics = []
    for data in learner_model._data.values():
        all_topics += list(data.get("topics", {}).keys())
    notes = []
    for topic in topics:
        for matched_topic in resolve_topics(topic, all_topics):
            for data in learner_model._data.values():
                t = data.get("topics", {}).get(matched_topic)
                if t and t.get("progress"):
                    notes.append(t["progress"])
    if not notes:
        return ""
    return "\n".join(f"- {n}" for n in notes)


def _build_messages(context: list[dict], topics: list[str], n: int, learner_context: str | None) -> list[dict]:
    content = []
    if learner_context:
        content.append({"type": "text", "text": f"Student progress notes:\n{learner_context}"})
    for block in context:
        if block.get("type") == "image":
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": block["source"]["data"]},
            })
        elif block.get("type") == "text":
            content.append({"type": "text", "text": block["text"]})
    content.append({"type": "text", "text": f"Topics: {', '.join(topics)}\n\n{QUIZ_GENERATION_PROMPT.format(n=n)}"})
    return [{"role": "user", "content": content}]


def generate_quiz(topics: list[str], n: int = DEFAULT_NUM_QUESTIONS, learner_model=None) -> Quiz:
    """Generate a quiz covering the given topics."""
    slides = retrieve(queries=topics)
    slide_lookup = {(s['deck'], s['slide_num']): s for s in slides}

    slide_context = build_context(slides)
    learner_context = _build_learner_context(topics, learner_model)
    messages = _build_messages(slide_context, topics, n, learner_context)

    text = call_anthropic(messages=messages, max_tokens=512 * n).strip()

    if text.lower() == "none":
        return Quiz(topics=topics, questions=[])

    questions = []
    for block in re.split(r"\n---\n?", text):
        result = _parse_question(block)
        if result is None:
            continue
        q, sources = result
        for src in sources:
            m = re.match(r'^(.+),\s*Slide\s*(\d+)$', src.strip(), re.IGNORECASE)
            if m:
                key = (m.group(1).strip(), int(m.group(2)))
                if key in slide_lookup:
                    q.slides.append(slide_lookup[key])
        questions.append(q)

    return Quiz(topics=topics, questions=questions)
