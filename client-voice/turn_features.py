"""Whisper 80-bin Slaney log-mel features for Smart Turn, numpy only.

Validated against transformers.WhisperFeatureExtractor(chunk_length=8).
"""
import numpy as np

def _mel(frequencies):
    frequencies=np.asarray(frequencies,dtype=np.float64)
    result=frequencies/(200/3)
    high=frequencies>=1000
    result[high]=15+np.log(frequencies[high]/1000)/(np.log(6.4)/27)
    return result

def _hz(mels):
    result=mels*(200/3)
    high=mels>=15
    result[high]=1000*np.exp((mels[high]-15)*(np.log(6.4)/27))
    return result

def features(audio):
    audio=np.asarray(audio,dtype=np.float32)[-128000:]
    audio=np.pad(audio,(128000-len(audio),0))
    audio=(audio-audio.mean())/np.sqrt(audio.var()+1e-7)
    padded=np.pad(audio,(200,200),mode='reflect')
    frames=np.lib.stride_tricks.sliding_window_view(padded,400)[::160]
    window=np.hanning(401)[:-1]
    power=np.abs(np.fft.rfft(frames*window,axis=1))**2
    frequencies=np.linspace(0,8000,201)
    bounds=_hz(np.linspace(_mel(np.array([0]))[0],_mel(np.array([8000]))[0],82))
    down=(frequencies[:,None]-bounds[:-2])/(bounds[1:-1]-bounds[:-2])
    up=(bounds[2:]-frequencies[:,None])/(bounds[2:]-bounds[1:-1])
    filters=np.maximum(0,np.minimum(down,up))* (2/(bounds[2:]-bounds[:-2]))
    values=np.log10(np.maximum(1e-10,(power@filters).T[:,:-1]))
    values=np.maximum(values,values.max()-8)
    return ((values+4)/4)[None].astype(np.float32)
