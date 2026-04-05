import json
from datetime import datetime, timezone
from pathlib import Path

LEARNER_MODEL_PATH = Path("data/learner_model.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearnerModel:
    def __init__(self, path: Path = LEARNER_MODEL_PATH):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def _topic(self, deck: str, topic: str) -> dict:
        self._data.setdefault(deck, {}).setdefault("topics", {}).setdefault(topic, {
            "progress": None,
            "last_seen": None,
            "history": [],
        })
        return self._data[deck]["topics"][topic]

    def add_deck(self, deck: str, summary: str, topics: list[str]) -> None:
        self._data.setdefault(deck, {})
        self._data[deck]["summary"] = summary
        for topic in topics:
            self._topic(deck, topic)
        self._save()

    def update_progress(self, deck: str, topic: str, progress: str) -> None:
        entry = self._topic(deck, topic)
        if entry["progress"]:
            entry["history"].append({"note": entry["progress"], "timestamp": entry["last_seen"]})
        entry["progress"] = progress
        entry["last_seen"] = _now()
        self._save()

    def get_deck(self, deck: str) -> dict:
        return self._data.get(deck, {})

    def get_topic(self, deck: str, topic: str) -> dict | None:
        return self._data.get(deck, {}).get("topics", {}).get(topic)

    def get_unseen_topics(self, deck: str) -> list[str]:
        topics = self._data.get(deck, {}).get("topics", {})
        return [name for name, t in topics.items() if t.get("progress") is None]
