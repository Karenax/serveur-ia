"""Explicit EG2 device selection and observable GPU-to-CPU recovery."""
import json
from pathlib import Path
import re
import subprocess
from core import ROOT,HIDDEN

CONFIG=Path(__file__).with_name('eg2-runtime.json')
CPU_PYTHON=ROOT/'toolchain/eg2-python/Scripts/python.exe'


def configuration(path=CONFIG):
    if not path.is_file():return {'device':'cpu','batch_size':4,'cpu_fallback':True}
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('device') not in ('cpu','cuda'):raise ValueError('Périphérique EG2 invalide.')
    if type(value.get('batch_size')) is not int or not 1<=value['batch_size']<=4:raise ValueError('Groupe EG2 invalide.')
    if type(value.get('cpu_fallback')) is not bool:raise ValueError('Repli EG2 invalide.')
    if value['device']=='cuda':
        if not re.fullmatch(r'GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value.get('gpu_uuid','')):raise ValueError('Carte EG2 invalide.')
        python=(ROOT/value.get('python','')).resolve()
        if not python.is_relative_to(ROOT/'toolchain') or python.name.lower()!='python.exe':raise ValueError('Runtime EG2 invalide.')
        for name in ('memory_limit_mib','minimum_free_mib'):
            if type(value.get(name)) is not int or value[name]<256:raise ValueError('Budget mémoire EG2 invalide.')
        value['python']=str(python)
    return value


def gpu_free_mib(uuid):
    raw=subprocess.check_output(['nvidia-smi','--id='+uuid,'--query-gpu=memory.free',
        '--format=csv,noheader,nounits'],text=True,timeout=3,creationflags=HIDDEN)
    return int(raw.strip())


class ModelRuntime:
    def __init__(self,model,torch,device='cpu',gpu_uuid='',memory_limit_mib=2200,
                 minimum_free_mib=1024,cpu_fallback=True,fallback_reason=''):
        self.model=model;self.torch=torch;self.requested_device=device;self.gpu_uuid=gpu_uuid
        self.minimum_free_mib=minimum_free_mib;self.cpu_fallback=cpu_fallback
        self.device='cpu';self.gpu_name='';self.fallback_reason=fallback_reason
        if device=='cuda':
            try:
                if not torch.cuda.is_available():raise RuntimeError('CUDA indisponible.')
                # The parent restricts visible devices to this UUID, never the RTX.
                if gpu_free_mib(gpu_uuid)<memory_limit_mib+minimum_free_mib:
                    raise RuntimeError('Mémoire GPU insuffisante au démarrage.')
                total=torch.cuda.get_device_properties(0).total_memory
                torch.cuda.set_per_process_memory_fraction(memory_limit_mib*2**20/total,0)
                self.model.to('cuda:0');self.device='cuda:0';self.gpu_name=torch.cuda.get_device_name(0)
            except (RuntimeError,OSError,ValueError,subprocess.SubprocessError) as error:
                if not cpu_fallback:raise
                self.to_cpu(str(error))

    def to_cpu(self,reason):
        self.model.to('cpu')
        self.device='cpu';self.gpu_name='';self.fallback_reason=reason
        if self.torch.cuda.is_available():self.torch.cuda.empty_cache()

    def encode(self,texts,**kwargs):
        if self.device.startswith('cuda'):
            try:
                if gpu_free_mib(self.gpu_uuid)<self.minimum_free_mib:
                    raise RuntimeError('Marge mémoire GPU insuffisante ; calcul sur CPU.')
            except (RuntimeError,OSError,ValueError,subprocess.SubprocessError) as error:
                if not self.cpu_fallback:raise
                self.to_cpu(str(error))
        try:return self.model.encode(texts,**kwargs)
        except self.torch.cuda.OutOfMemoryError:
            if self.device=='cpu' or not self.cpu_fallback:raise
            self.to_cpu('Mémoire GPU saturée ; calcul repris sur CPU.')
            return self.model.encode(texts,**kwargs)

    def status(self):
        return {'device':self.device,'requested_device':self.requested_device,
            'gpu_uuid':self.gpu_uuid,'gpu_name':self.gpu_name,'fallback_reason':self.fallback_reason}
