from colpali_engine.models import ColIdefics3, ColIdefics3Processor
import torch

MODEL_ID = 'vidore/colSmol-256M'

_model = None
_processor = None

def load_model():
    global _model, _processor
    if _model is None:
        device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        print(f"[model] Loading {MODEL_ID} on {device}...")
        _model = ColIdefics3.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map=device)
        _processor = ColIdefics3Processor.from_pretrained(MODEL_ID)
        print(f"[model] Ready")
    return _model, _processor
