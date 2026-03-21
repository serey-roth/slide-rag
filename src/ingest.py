import argparse
from pathlib import Path
from PIL import Image
import numpy as np
import json
import shutil

from dotenv import load_dotenv
load_dotenv()

from pdf2image import convert_from_path
import torch
from src.model import load_model


def _load_images(folder: Path) -> list:
    files = sorted(folder.glob('*.png')) or sorted(folder.glob('*.jpg')) or sorted(folder.glob('*.ppm'))
    return [Image.open(p).convert('RGB') for p in files]


def convert_pdf_to_images(pdf_path: str, force: bool = False) -> tuple[list, Path]:
    path = Path(pdf_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    deck_name = path.stem
    images_dir = Path('data/images') / deck_name

    if force and images_dir.exists():
        print(f"[pdf] Clearing cached images for {deck_name}...")
        shutil.rmtree(images_dir)

    if not images_dir.exists():
        images_dir.mkdir(parents=True, exist_ok=True)
        print(f"[pdf] Converting {path.name} to images...")
        convert_from_path(str(path), fmt='png', output_folder=images_dir, output_file=deck_name)
        images = _load_images(images_dir)
        print(f"[pdf] Done — {len(images)} slides → {images_dir}")
    else:
        images = _load_images(images_dir)
        print(f"[pdf] Loaded {len(images)} cached slides from {images_dir}")

    if not images:
        raise RuntimeError(f"No slide images found in {images_dir}.")

    return images, images_dir


def create_embeddings(images: list, model, processor) -> torch.Tensor:
    print(f"[embed] Embedding {len(images)} slides...")
    all_embeddings = []
    for i, img in enumerate(images):
        batch = processor.process_images([img]).to(model.device)
        with torch.inference_mode():
            emb = model(**batch)
        all_embeddings.append(emb.cpu())
        print(f"[embed] {i + 1}/{len(images)}")
    image_embeddings = torch.cat(all_embeddings, dim=0)
    print(f"[embed] Done — shape {image_embeddings.shape}")
    return image_embeddings


def store_embeddings(deck_name: str, images_dir: Path, image_embeddings: torch.Tensor, images: list) -> tuple[Path, Path]:
    index_dir = Path('data/indexes') / deck_name
    index_dir.mkdir(parents=True, exist_ok=True)

    embeddings_path = index_dir / 'patch_embeddings.npy'
    np.save(embeddings_path, image_embeddings.cpu().to(torch.float32).numpy())
    print(f"[store] Saved embeddings → {embeddings_path}")

    index_path = index_dir / 'slide_index.json'
    image_files = sorted(images_dir.glob('*.png')) or sorted(images_dir.glob('*.jpg'))
    slide_index = [
        {'slide_num': i + 1, 'image_path': str(image_files[i])}
        for i in range(len(images))
    ]
    index_path.write_text(json.dumps(slide_index, indent=2))
    print(f"[store] Saved slide index → {index_path}")

    return embeddings_path, index_path


def embed_slides(deck_name: str, images: list, images_dir: Path, model, processor, force: bool = False) -> tuple:
    index_dir = Path('data/indexes') / deck_name
    embeddings_path = index_dir / 'patch_embeddings.npy'
    index_path = index_dir / 'slide_index.json'

    if force and index_dir.exists():
        print(f"[embed] Clearing cached embeddings for {deck_name}...")
        shutil.rmtree(index_dir)

    if not embeddings_path.exists() or not index_path.exists():
        image_embeddings = create_embeddings(images, model, processor)
        store_embeddings(deck_name, images_dir, image_embeddings, images)
    else:
        image_embeddings = torch.from_numpy(np.load(embeddings_path))
        print(f"[embed] Loaded cached embeddings — shape {image_embeddings.shape}")

    slide_index = json.loads(index_path.read_text())
    return image_embeddings, slide_index

def ingest(pdf_path: str, force: bool = False) -> None:
    deck_name = Path(pdf_path).stem

    print(f"[ingest] {deck_name}  {'(force rebuild)' if force else ''}")

    images, images_dir = convert_pdf_to_images(pdf_path, force=force)

    model, processor = load_model()

    embed_slides(deck_name, images, images_dir, model, processor, force=force)

    print(f"[ingest] Done — {deck_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a PDF slide deck using ColPali visual embeddings.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--force", action="store_true", help="Clear and rebuild cached images and embeddings")
    args = parser.parse_args()
    ingest(args.pdf_path, force=args.force)
