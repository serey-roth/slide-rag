from dataclasses import dataclass
from typing import Literal
import re

import anthropic
from dotenv import load_dotenv

load_dotenv()

from src.config import ORCHESTRATOR_MODEL

_anthropic = anthropic.Anthropic()

ORCHESTRATOR_PROMPT = """\
You are a routing agent. Classify the user's latest message into exactly one intent.
If recent messages are provided, use them to resolve vague references like "this" or "that topic".

Routes:
- qa: user asks a question or wants an explanation
- quiz: user wants a quiz or practice test
- quit: user wants to stop or exit
- none: anything else

Respond in this exact format:
intent_type: <qa | quiz | quit | none>
topic: <fully resolved topic if quiz>
query: <fully resolved question if qa>
intent_reason: <one sentence explaining the chosen intent>\
"""


@dataclass
class Intent:
    type: Literal['qa', 'quiz', 'quit', 'none']
    topic: str | None
    query: str | None
    reason: str


def classify(query: str, recent_queries: list[str] | None = None) -> Intent:
    context = ""
    if recent_queries:
        history_text = "\n".join(f"- {q}" for q in recent_queries)
        context = f"Recent user messages:\n{history_text}\n\n"

    response = _anthropic.messages.create(
        model=ORCHESTRATOR_MODEL,
        system=ORCHESTRATOR_PROMPT,
        max_tokens=150,
        messages=[{"role": "user", "content": f"{context}Latest message: {query}"}],
    )
    text = response.content[0].text

    type_m = re.search(r"^intent_type:\s*(\w+)", text, re.IGNORECASE | re.MULTILINE)
    topic_m = re.search(r"^topic:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    query_m = re.search(r"^query:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    reason_m = re.search(r"^intent_reason:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)

    return Intent(
        type=type_m.group(1).strip().lower() if type_m else "none",
        topic=topic_m.group(1).strip() if topic_m else None,
        query=query_m.group(1).strip() if query_m else None,
        reason=reason_m.group(1).strip() if reason_m else "",
    )


if __name__ == "__main__":
    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query or query.lower() in {"quit", "exit", "q"}:
            break

        intent = classify(query)
        print(f"  → {intent}\n")
