from dataclasses import dataclass, field
from typing import Any

MAX_HISTORY_TURNS = 6

CHAT_HISTORY_STORAGE_KEY = 'chat_history'


def _is_valid_history_entry(x: Any) -> bool:
    return isinstance(x, dict) and isinstance(x.get('role'), str) and isinstance(x.get('content'), str)


def chat_session_from_storage(user_storage: dict) -> 'SessionState':
    raw = user_storage.get(CHAT_HISTORY_STORAGE_KEY)
    if isinstance(raw, list) and all(_is_valid_history_entry(x) for x in raw):
        return SessionState(history=raw)
    return SessionState()


def persist_chat_session(user_storage: dict, session: 'SessionState') -> None:
    user_storage[CHAT_HISTORY_STORAGE_KEY] = list(session.history)


@dataclass
class SessionState:
    history: list[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-(MAX_HISTORY_TURNS * 2):]
