import re

from src.retrieve import build_context, retrieve

import anthropic

_anthropic = anthropic.Anthropic()

QA_MODEL = "claude-sonnet-4-6"

QA_PROMPT = """\
You are a helpful tutor answering a graduate student's questions about their lectures.
You have been given a set of slides from their lecture decks.

Rules:
- Ground your answer in the provided slides whenever possible.
- If the slides are sparse or incomplete, supplement with accurate knowledge \
to fully explain the concept. Clearly indicate when you are going beyond what the slides say.
- Always cite sources using the format [deck_name, Slide X], e.g. [week1, Slide 12].
- If you are uncertain, say so. Do not fabricate facts.
- Be concise but thorough. Explain the "why", not just the "what".
- Use the conversation history to answer follow-up questions naturally.\
"""

def ask_question(query: str, history: list[dict], deck_filter: str | list[str] | None) -> tuple[str, list[tuple[int, str]]]:
    slides = retrieve(query, deck_filter)
    context = build_context(slides)
    messages = list(history) + [{
        "role": "user",
        "content": f"Relevant slides:\n\n{context}\n\nQuestion: {query}",
    }]

    full_response = ""
    with _anthropic.messages.stream(
        model=QA_MODEL,
        max_tokens=1024,
        system=QA_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text
    print()

    citations = list(dict.fromkeys(
        re.findall(r"\[([^\]]+,\s*Slide\s*\d+)\]", full_response)
    ))

    return full_response, citations