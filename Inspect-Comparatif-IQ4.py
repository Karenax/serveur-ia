"""Inspect local GGUF headers without reading the model's large weight payloads."""
import collections
import hashlib
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Strata-src' / 'tools'))
from gguf_reader import GGUFFile

folder = Path('D:/modèle/qwen3.8FlashNext')
families = {'q4': 'Qwen3.8-Flash-Next-UD-Q4_K_XL',
            'iq4': 'Qwen3.8-Flash-Next-Uncensored-IQ4_XS'}
models = {}
for label, prefix in families.items():
    paths = sorted(folder.glob(prefix + '-*.gguf'))
    if not paths:
        raise FileNotFoundError(prefix)
    files = [GGUFFile(path) for path in paths]
    tensors = {}
    shards = []
    for path, file in zip(paths, files):
        if file.metadata.get('split.count', len(paths)) != len(paths):
            raise ValueError('inconsistent shard count')
        for tensor in file.tensors:
            size = tensor.expected_bytes()
            if size is None or file.data_start + tensor.offset + size > path.stat().st_size:
                raise ValueError(f'truncated or unsupported tensor {tensor.name}')
            if tensor.name in tensors:
                raise ValueError('duplicate tensor ' + tensor.name)
            tensors[tensor.name] = tensor
        with path.open('rb') as stream:
            header_sha = hashlib.sha256(stream.read(file.data_start)).hexdigest()
        shards.append(dict(name=path.name, size=path.stat().st_size,
                           header_sha256=header_sha, tensor_types=file.by_type()))
    meta = files[0].metadata
    shape_hash = hashlib.sha256(json.dumps(
        {name: t.shape for name, t in sorted(tensors.items())},
        sort_keys=True).encode()).hexdigest()
    token_meta = {key: value for key, value in meta.items() if key.startswith('tokenizer.')}
    token_hash = hashlib.sha256(json.dumps(token_meta, sort_keys=True).encode()).hexdigest()
    experts = [t for t in tensors.values() if t.name.endswith('_exps.weight')]
    models[label] = dict(
        metadata={key: value for key, value in meta.items()
                  if not key.startswith('tokenizer.') and not isinstance(value, list)},
        shards=shards, total_bytes=sum(p.stat().st_size for p in paths),
        expert_bytes=sum(t.expected_bytes() for t in experts),
        expert_types=dict(collections.Counter(t.type_name for t in experts)),
        shape_sha256=shape_hash, tokenizer_metadata_sha256=token_hash,
        important_tensors={name: dict(shape=tensors[name].shape,
                                     type=tensors[name].type_name,
                                     bytes=tensors[name].expected_bytes())
                           for name in ('per_layer_token_embd.weight', 'token_embd.weight',
                                        'output.weight', 'blk.1.ple_key.weight') if name in tensors})

print(json.dumps(models, ensure_ascii=False, indent=2))
