import re
from typing import Callable

from src.retrieve import build_context, retrieve

import anthropic

_anthropic = anthropic.Anthropic()

QA_MODEL = "claude-sonnet-4-6"

QA_PROMPT = """\
You are a helpful tutor answering a graduate student's questions about their lectures.
You have been given slide images from their lecture decks.

Rules:
- Read each slide image carefully, including diagrams, equations, code, and figures.
- Ground your answer in what you see in the slides whenever possible.
- Always cite sources using the format [deck_name, Slide X], e.g. [week1, Slide 12].
- If the slides do not fully cover the question, supplement with accurate knowledge \
and clearly indicate when you are going beyond the slides.
- If you are uncertain, say so. Do not fabricate facts.
- Be concise but thorough. Explain the "why", not just the "what".
- Use the conversation history to answer follow-up questions naturally.\
"""

def ask_question(
    query: str,
    history: list[dict],
    deck_filter: str | list[str] | None,
    on_stream: Callable[[str], None] | None = None,
    on_slides: Callable[[list[dict]], None] | None = None,
) -> tuple[str, list[str], list[dict]]:
    slides = retrieve(queries=[query], deck_filter=deck_filter)
    if on_slides:
        on_slides(slides)
    context = build_context(slides)
    messages = list(history) + [{
        "role": "user",
        "content": context + [{"type": "text", "text": f"Question: {query}"}],
    }]

    full_response = ""
    with _anthropic.messages.stream(
        model=QA_MODEL,
        max_tokens=1024,
        system=QA_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            if on_stream:
                on_stream(text)

    citations = list(dict.fromkeys(
        re.findall(r"\[([^\]]+,\s*Slide\s*\d+)\]", full_response)
    ))

    return full_response, citations, slides


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ask a question using the VLM-based QA pipeline.")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--decks", nargs="+", help="Filter to specific deck names", default=None)
    args = parser.parse_args()

    response, citations = ask_question(args.query, history=[], deck_filter=args.decks, on_stream=print)
    if citations:
        print(f"\nCitations: {', '.join(citations)}")