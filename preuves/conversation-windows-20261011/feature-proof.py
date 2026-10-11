import json
from pathlib import Path
import sys
import numpy as np
from transformers import WhisperFeatureExtractor
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'client-voice'))
from turn_features import features
audio=np.random.default_rng(42).normal(0,.1,128000).astype(np.float32)
reference=WhisperFeatureExtractor(chunk_length=8)(audio,sampling_rate=16000,return_tensors='np',padding='max_length',max_length=128000,truncation=True,do_normalize=True).input_features
actual=features(audio);error=float(np.max(np.abs(actual-reference)));assert error<1e-5
(Path(__file__).resolve().parent/'smart-turn-features.json').write_text(json.dumps({'passed':True,'shape':list(actual.shape),'max_absolute_error':error,'tolerance':1e-5,'reference':'transformers.WhisperFeatureExtractor(chunk_length=8)'},indent=2),encoding='utf-8')
print('Smart Turn features match official extractor:',error)
