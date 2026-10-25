"""Bounded, French Whisper Turbo recognition on the selected Vulkan adapter."""
import ctypes as c
import os
from pathlib import Path
import threading
import numpy as np

Cancel=c.CFUNCTYPE(c.c_bool,c.c_void_p)


class GPUInfo(c.Structure):
    _fields_=[('name',c.c_char*64),('description',c.c_char*256),('pci_id',c.c_char*128),
              ('kind',c.c_int),('free_bytes',c.c_size_t),('total_bytes',c.c_size_t)]


def library(root):
    folder=Path(root)/'native'
    if os.name=='nt':os.add_dll_directory(str(folder))
    lib=c.CDLL(str(folder/'kiara-asr.dll'))
    lib.ka_gpu_info_size.restype=c.c_int
    if lib.ka_gpu_info_size()!=c.sizeof(GPUInfo):raise ValueError('Le moteur vocal Max doit être mis à jour.')
    lib.ka_gpu_info.argtypes=[c.c_int,c.POINTER(GPUInfo)]
    lib.ka_gpu_count.restype=c.c_int
    lib.ka_error.restype=c.c_char_p
    return lib


def available_devices(root):
    from max_gpu import gpu_id
    lib=library(root);cards=[]
    for index in range(lib.ka_gpu_count()):
        info=GPUInfo()
        if lib.ka_gpu_info(index,c.byref(info)):continue
        item={'name':info.name.decode(),'description':info.description.decode(),
              'pci_id':info.pci_id.decode(),'kind':{1:'dedicated',2:'integrated'}.get(info.kind,'other'),
              'free_bytes':info.free_bytes,'total_bytes':info.total_bytes}
        item['id']=gpu_id(item);cards.append(item)
    return cards


class WhisperRecognition:
    def __init__(self,root,selection='auto',device=None):
        from max_gpu import select_gpu,GPUCompatibilityError
        self.lib=library(root);self.device_info={};self.audio=bytearray();self.key=None
        if device is None:
            self.device_info=dict(select_gpu(available_devices(root),selection));device=self.device_info['name']
        self.lib.ka_open.argtypes=[c.c_char_p,c.c_char_p];self.lib.ka_open.restype=c.c_void_p
        self.lib.ka_transcribe.argtypes=[c.c_void_p,c.POINTER(c.c_float),c.c_int,c.c_bool,Cancel,c.c_void_p]
        self.lib.ka_transcribe.restype=c.c_char_p;self.lib.ka_close.argtypes=[c.c_void_p]
        self.handle=self.lib.ka_open(str(Path(root)/'asr/ggml-large-v3-turbo-q5_0.bin').encode('utf-8'),device.encode())
        if not self.handle:raise GPUCompatibilityError('Le chargement de la reconnaissance Max a échoué sur la carte choisie. Vérifiez les fichiers et le pilote Vulkan.')

    def transcribe(self,command,cancelled=None):
        raw=command['raw_pcm'];key=command.get('stream_key');final=command.get('final',True)
        if len(raw)%2 or len(raw)>28*16000*2:raise ValueError('Son Max incomplet ou trop long.')
        if key is None or key!=self.key:self.audio.clear();self.key=key
        offset=command.get('offset',0)
        if offset*2>len(self.audio):raise ValueError('Segment vocal manquant. Répétez votre phrase.')
        del self.audio[offset*2:];self.audio.extend(raw)
        if len(self.audio)>28*16000*2:raise ValueError('Phrase vocale trop longue.')
        if len(self.audio)<1600*2:return ''
        samples=np.frombuffer(self.audio,dtype='<i2').astype(np.float32)/32768
        @Cancel
        def stop(_):return cancelled is not None and cancelled.is_set()
        text=self.lib.ka_transcribe(self.handle,samples.ctypes.data_as(c.POINTER(c.c_float)),len(samples),final,stop,None)
        if cancelled is not None and cancelled.is_set():return ''
        if text is None:raise ValueError('La reconnaissance Max a échoué. Réessayez votre phrase.')
        value=text.decode('utf-8').strip()[:6000]
        if final:self.audio.clear();self.key=None
        return value

    def close(self):
        if self.handle:self.lib.ka_close(self.handle);self.handle=None
