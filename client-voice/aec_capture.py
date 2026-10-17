"""Same-thread COM capture through the Windows Voice Capture DSP."""
import ctypes
import time
from pathlib import Path

class EchoMicrophone:
    def __init__(self, resources):
        self.dll=ctypes.CDLL(str(Path(resources)/'fredaec.dll'))
        self.dll.fred_aec_open.argtypes=[];self.dll.fred_aec_open.restype=ctypes.c_void_p
        self.dll.fred_aec_read.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int]
        self.dll.fred_aec_read.restype=ctypes.c_int
        self.dll.fred_aec_close.argtypes=[ctypes.c_void_p]
        self.dll.fred_aec_close.restype=None
        self.handle=self.dll.fred_aec_open()
        if not self.handle:
            raise OSError('Capture avec annulation d’écho indisponible. Vérifiez les périphériques audio Windows par défaut.'+self.error_code())
        self.buffer=ctypes.create_string_buffer(3200)
    def read(self):
        n=self.dll.fred_aec_read(self.handle,self.buffer,len(self.buffer))
        if n<0:raise OSError('Le microphone avec annulation d’écho a été interrompu.'+self.error_code())
        if not n:time.sleep(.01)
        return self.buffer.raw[:n]
    def close(self):
        if self.handle:self.dll.fred_aec_close(self.handle);self.handle=None
    def error_code(self):
        if not hasattr(self.dll,'fred_aec_last_error'):return ''
        self.dll.fred_aec_last_error.restype=ctypes.c_long
        return ' Code Windows : 0x%08X.'%(self.dll.fred_aec_last_error()&0xffffffff)
