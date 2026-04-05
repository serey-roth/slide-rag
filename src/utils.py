from pathlib import Path


DECKS_DIR = Path('data/decks')

def get_decks() -> list[str]:
    return sorted(p.stem for p in DECKS_DIR.glob('*.pdf'))