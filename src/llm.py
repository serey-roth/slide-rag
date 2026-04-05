
import os
from typing import Callable

import anthropic
import requests
from dotenv import load_dotenv
load_dotenv()

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
LOCAL_MODEL = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
COLPALI_MODEL = 'vidore/colSmol-256M'


def call_anthropic(
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 1024,
    model: str = CLAUDE_MODEL,
) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def call_anthropic_stream(
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 1024,
    on_token: Callable[[str], None] | None = None,
    model: str = CLAUDE_MODEL,
) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    full = ""
    with client.messages.stream(**kwargs) as stream:
        for token in stream.text_stream:
            full += token
            if on_token:
                on_token(token)
    return full


def call_ollama(
    prompt: str,
    model: str = LOCAL_MODEL,
    num_predict: int = 80,
) -> str:
    result = requests.post(OLLAMA_URL, json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict},
    })
    result.raise_for_status()
    return result.json()["response"].strip()


from colpali_engine.models import ColIdefics3, ColIdefics3Processor
import torch

_model = None
_processor = None

def load_colpali_model():
    global _model, _processor
    if _model is None:
        device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        print(f"[model] Loading {COLPALI_MODEL} model on {device}...")
        _model = ColIdefics3.from_pretrained(COLPALI_MODEL, torch_dtype=torch.float16, device_map=device)
        _processor = ColIdefics3Processor.from_pretrained(COLPALI_MODEL)
        print(f"[model] Colpali model ready")
    return _model, _processor
