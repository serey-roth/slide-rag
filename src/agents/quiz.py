from dataclasses import dataclass
from typing import Callable
import re

import anthropic

from src.retrieve import build_context, retrieve

_anthropic = anthropic.Anthropic()

QUIZ_GENERATION_MODEL = 'claude-haiku-4-5'
DEFAULT_NUM_QUESTIONS = 5

QUIZ_GENERATION_PROMPT = """
You are a quiz maker helping a student learn a topic from lecture slide images.
Given a topic and slide images, generate {n} multiple-choice questions grounded in what you see in the slides.
Read each slide carefully, including diagrams, equations, code, and figures.

Respond in EXACTLY this format with no extra text, no markdown, no bold.
Separate each question with ---:

question: <question text>
options:
- <option 1>
- <option 2>
- <option 3>
- <option 4>
answer: <exact text of correct option>
sources: [deck_name, Slide X], [deck_name, Slide Y]
---

If the topic has no relevant slide content, respond with exactly: None
"""


@dataclass
class Question:
    prompt: str
    options: list[str]
    answer: int
    sources: list[str]

@dataclass
class Quiz:
    topic: str
    questions: list[Question]


def _parse_question(block: str) -> Question | None:
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
        sources=sources,
    )



def generate_quiz(topic: str, deck_filter: str | list[str] | None, n: int = DEFAULT_NUM_QUESTIONS) -> Quiz:
    slides = retrieve(queries=[topic], deck_filter=deck_filter)
    context = build_context(slides)

    response = _anthropic.messages.create(
        model=QUIZ_GENERATION_MODEL,
        system=QUIZ_GENERATION_PROMPT.format(n=n),
        max_tokens=512 * n,
        messages=[{
            "role": "user",
            "content": context + [{"type": "text", "text": f"Topic: {topic}"}],
        }],
    )

    text = response.content[0].text.strip()

    if text.lower() == "none":
        return Quiz(topic=topic, questions=[])

    blocks = re.split(r"\n---\n?", text)
    questions = [q for block in blocks if (q := _parse_question(block))]
    return Quiz(topic=topic, questions=questions)


def run_quiz(quiz: Quiz, on_wrong: Callable[[Question], None] | None = None) -> None:
    if not quiz.questions:
        print("No questions generated (topic did not match slide content).")
        return

    correct = 0
    total = len(quiz.questions)

    for i, q in enumerate(quiz.questions, start=1):
        print(f"\n{'─' * 50}")
        print(f"  Q{i}/{total}  {q.prompt}")
        print(f"{'─' * 50}\n")
        for j, option in enumerate(q.options):
            print(f"    {j})  {option}")

        while True:
            raw = input("\n  Your answer (0-3): ").strip()
            if raw.isdigit() and 0 <= int(raw) < len(q.options):
                break
            print("  Please enter a number between 0 and 3.")

        chosen = int(raw)
        if chosen == q.answer:
            print("  ✓ Correct!")
            correct += 1
        else:
            print(f"  ✗ Wrong — correct answer: {q.options[q.answer]}")
            if on_wrong:
                on_wrong(q)

        if q.sources:
            print(f"  Source: {', '.join(f'[{s}]' for s in q.sources)}")

    pct = round(correct / total * 100)
    print(f"\n{'═' * 50}")
    print(f"  Results: {correct}/{total} correct  ({pct}%)")
    print(f"{'═' * 50}\n")


if __name__ == "__main__":
    print("Quiz Generator — enter a topic to start a quiz, or 'quit' to exit.\n")
    while True:
        topic = input("Topic: ").strip()
        if topic.lower() in ("quit", "exit", "q"):
            break
        if not topic:
            continue
        print("Generating quiz...")
        quiz = generate_quiz(topic, deck_filter=None)
        run_quiz(quiz)
        print()
