"""Fetch the pinned public model. Runtime inference never downloads anything."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

revision='914f7f89142e33e77833254d9c9b90c3cef7303b'
target=Path(__file__).resolve().parent.parent/'toolchain'/'eg2-model'
snapshot_download('google/embeddinggemma-2',revision=revision,local_dir=target,
    allow_patterns=['*.json','*.safetensors','*.model','*.jinja','1_Pooling/*','2_Normalize/*','README.md'])
(target/'fred-model.json').write_text(json.dumps({'repo':'google/embeddinggemma-2','revision':revision}),encoding='utf-8')
print('EmbeddingGemma 2 installé :',target)
