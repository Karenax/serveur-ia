"""Pinned qwentts.cpp ABI 6: streaming French voice with bounded output and cancellation."""
import array
import ctypes as c
import hashlib
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from french_voice import reference
from max_gpu import gpu_id, GPUCompatibilityError, gpu_candidates, select_gpu

Cancel = c.CFUNCTYPE(c.c_bool, c.c_void_p)
Chunk = c.CFUNCTYPE(c.c_bool, c.POINTER(c.c_float), c.c_int, c.c_void_p)


class Init(c.Structure):
    _fields_ = [('abi_version', c.c_int), ('talker_path', c.c_char_p), ('codec_path', c.c_char_p),
                ('use_fa', c.c_bool), ('clamp_fp16', c.c_bool), ('max_batch', c.c_int),
                ('codec_chunk_sec', c.c_float), ('device', c.c_char_p)]


class Audio(c.Structure):
    _fields_ = [('samples', c.POINTER(c.c_float)), ('n_samples', c.c_int),
                ('sample_rate', c.c_int), ('channels', c.c_int)]


class Params(c.Structure):
    _fields_ = [('abi_version', c.c_int), ('text', c.c_char_p), ('lang', c.c_char_p),
                ('instruct', c.c_char_p), ('speaker', c.c_char_p), ('ref_audio_24k', c.POINTER(c.c_float)),
                ('ref_n_samples', c.c_int), ('ref_text', c.c_char_p), ('seed', c.c_int64),
                ('max_new_tokens', c.c_int), ('temperature', c.c_float), ('top_k', c.c_int),
                ('top_p', c.c_float), ('repetition_penalty', c.c_float), ('subtalker_temperature', c.c_float),
                ('subtalker_top_k', c.c_int), ('subtalker_top_p', c.c_float), ('dump_dir', c.c_char_p),
                ('cancel', Cancel), ('cancel_user_data', c.c_void_p), ('on_chunk', Chunk),
                ('on_chunk_user_data', c.c_void_p), ('ref_spk_emb', c.POINTER(c.c_float)),
                ('ref_spk_dim', c.c_int), ('ref_codes', c.POINTER(c.c_int32)), ('ref_T', c.c_int)]


class VoiceReference(c.Structure):
    _fields_=[('ref_spk_emb',c.POINTER(c.c_float)),('ref_spk_dim',c.c_int),
              ('ref_codes',c.POINTER(c.c_int32)),('ref_T',c.c_int),('num_codebooks',c.c_int)]


class DeviceCaps(c.Structure):
    _fields_=[(name,c.c_bool) for name in ('async_ops','host_buffer','buffer_from_host_ptr','event_sync','mmap_support')]


class DeviceProps(c.Structure):
    # Pinned GGML ABI: ggml/include/ggml-backend.h.
    _fields_=[('name',c.c_char_p),('description',c.c_char_p),('memory_free',c.c_size_t),
              ('memory_total',c.c_size_t),('type',c.c_int),('device_id',c.c_char_p),('caps',DeviceCaps)]




def available_devices(root):
    """Enumerate native backends without allocating model or GPU memory."""
    root = Path(root)
    if os.name == 'nt':
        directory = os.add_dll_directory(str(root/'native'))
    else:
        directory = None
    native = c.CDLL(str(root/'native/qwen.dll'))  # Load the same static backends as synthesis.
    loader = c.CDLL(str(root/'native/ggml.dll'))
    loader.ggml_backend_load_all()
    api = c.CDLL(str(root/'native/ggml-base.dll'))
    loader.ggml_backend_dev_count.restype = c.c_size_t
    loader.ggml_backend_dev_get.argtypes = [c.c_size_t]
    loader.ggml_backend_dev_get.restype = c.c_void_p
    for name in ('ggml_backend_dev_name', 'ggml_backend_dev_description'):
        getattr(api, name).argtypes = [c.c_void_p]
        getattr(api, name).restype = c.c_char_p
    api.ggml_backend_dev_memory.argtypes = [c.c_void_p, c.POINTER(c.c_size_t), c.POINTER(c.c_size_t)]
    api.ggml_backend_dev_get_props.argtypes=[c.c_void_p,c.POINTER(DeviceProps)]
    result = []
    for i in range(loader.ggml_backend_dev_count()):
        device = loader.ggml_backend_dev_get(i)
        free = c.c_size_t(); total = c.c_size_t()
        api.ggml_backend_dev_memory(device, c.byref(free), c.byref(total))
        props=DeviceProps();api.ggml_backend_dev_get_props(device,c.byref(props))
        item={'name': api.ggml_backend_dev_name(device).decode(),
                       'description': api.ggml_backend_dev_description(device).decode(),
                       'free_bytes': free.value, 'total_bytes': total.value,
                       'kind':{1:'dedicated',2:'integrated'}.get(props.type,'other'),
                       'pci_id':props.device_id.decode() if props.device_id else ''}
        item['id']=gpu_id(item);result.append(item)
    if directory:
        directory.close()
    return result








class NativeVoice:
    def __init__(self, root, device=None, selection='auto'):
        root = Path(root)
        self.dll_directory = os.add_dll_directory(str(root/'native')) if os.name == 'nt' else None
        self.lib = c.CDLL(str(root/'native/qwen.dll'))
        self.device_info={}
        if device is None:
            cards = available_devices(root)
            # Estimates help rank dedicated cards; shared host RAM never outranks VRAM.
            try:
                probe = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.free', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5, check=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                for line in probe.stdout.splitlines():
                    name, free = line.rsplit(',', 1)
                    for item in cards:
                        if item['description'].lower().replace('nvidia ', '').strip() == name.lower().replace('nvidia ', '').strip():
                            item['free_bytes'] = min(item['free_bytes'], int(free.strip())*1024**2)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.device_info=dict(select_gpu(cards,selection))
            device=self.device_info['name']
        self.lib.qt_version.restype = c.c_char_p
        if not self.lib.qt_version().decode().startswith('5916bf7'):
            raise ValueError('Version du moteur Max différente du complément vérifié.')
        self.lib.qt_init_default_params.argtypes = [c.POINTER(Init)]
        self.lib.qt_init.argtypes = [c.POINTER(Init)]
        self.lib.qt_init.restype = c.c_void_p
        self.lib.qt_tts_default_params.argtypes = [c.POINTER(Params)]
        self.lib.qt_synthesize.argtypes = [c.c_void_p, c.POINTER(Params), c.POINTER(Audio)]
        self.lib.qt_synthesize.restype = c.c_int
        self.lib.qt_audio_free.argtypes = [c.POINTER(Audio)]
        self.lib.qt_free.argtypes = [c.c_void_p]
        self.lib.qt_last_error.restype = c.c_char_p
        p = Init()
        self.lib.qt_init_default_params(c.byref(p))
        p.abi_version = 6
        p.talker_path = str(root/'tts/talker.gguf').encode()
        p.codec_path = str(root/'tts/codec.gguf').encode()
        p.device = device.encode()
        p.use_fa = False  # Portable AMD/NVIDIA kernels; no vendor-specific FA requirement.
        p.clamp_fp16 = True
        self.handle = self.lib.qt_init(c.byref(p))
        if not self.handle:
            raise GPUCompatibilityError('Le chargement du modèle Max sur la carte graphique a échoué. Vérifiez le pilote Vulkan et la mémoire disponible, puis réessayez. Ce résultat ne mesure pas la puissance du PC.')
        self.voice_reference=VoiceReference()
        try:
            self.lib.qt_model_type.argtypes=[c.c_void_p];self.lib.qt_model_type.restype=c.c_char_p
            if self.lib.qt_model_type(self.handle)!=b'base':
                raise ValueError('Le modèle français de Max doit être mis à jour depuis Vocal.')
            _,self.reference_text,samples=reference(root)
            pcm=(c.c_float*len(samples))(*samples)
            self.lib.qt_extract_voice_ref.argtypes=[c.c_void_p,c.POINTER(c.c_float),c.c_int,c.POINTER(VoiceReference)]
            self.lib.qt_extract_voice_ref.restype=c.c_int
            self.lib.qt_voice_ref_free.argtypes=[c.POINTER(VoiceReference)]
            if self.lib.qt_extract_voice_ref(self.handle,pcm,len(samples),c.byref(self.voice_reference)):
                raise ValueError('La préparation de la voix française Max a échoué. Vérifiez les fichiers du complément.')
            if (not self.voice_reference.ref_spk_emb or not self.voice_reference.ref_codes
                    or self.voice_reference.ref_spk_dim!=2048 or self.voice_reference.ref_T<=0 or self.voice_reference.num_codebooks!=16):
                raise ValueError('La référence française Max est incompatible avec ce modèle.')
        except Exception:
            self.close()
            raise

    def stream(self, text, cancelled):
        output = queue.Queue(maxsize=32)
        finished = threading.Event()
        failure = []
        started = time.perf_counter()
        measured = {'first_audio_ms': None, 'samples': 0}

        @Cancel
        def stop(_):
            return cancelled.is_set()

        @Chunk
        def chunk(samples, count, _):
            try:
                if count < 1 or count > 24000*4 or measured['samples']+count > 60*24000:
                    raise ValueError('Trame Max invalide ou trop longue.')
                if measured['first_audio_ms'] is None:
                    measured['first_audio_ms'] = (time.perf_counter()-started)*1000
                pcm = array.array('h')
                for i in range(count):
                    value = samples[i]
                    if not math.isfinite(value):
                        raise ValueError('Trame Max invalide.')
                    pcm.append(round(max(-1., min(1., value))*32767))
                measured['samples'] += count
                raw = pcm.tobytes()
                for offset in range(0, len(raw), 9600):
                    while not cancelled.is_set():
                        try:
                            output.put(raw[offset:offset+9600], timeout=.1)
                            break
                        except queue.Full:
                            continue
                    if cancelled.is_set():
                        return False
                return True
            except Exception as error:
                failure.append(error)
                cancelled.set()
                return False

        def run():
            result = Audio()
            try:
                p = Params()
                self.lib.qt_tts_default_params(c.byref(p))
                p.abi_version = 6
                p.text = text.encode('utf-8')
                p.lang = b'french'
                p.speaker = None
                p.instruct = None
                p.ref_text = self.reference_text.encode('utf-8')
                p.ref_spk_emb = self.voice_reference.ref_spk_emb
                p.ref_spk_dim = self.voice_reference.ref_spk_dim
                p.ref_codes = self.voice_reference.ref_codes
                p.ref_T = self.voice_reference.ref_T
                p.max_new_tokens = min(750, max(96, len(text)*4))
                p.cancel = stop
                p.on_chunk = chunk
                status = self.lib.qt_synthesize(self.handle, c.byref(p), c.byref(result))
                if status and not cancelled.is_set():
                    raise ValueError('La synthèse Max a échoué. Réessayez ou choisissez Low.')
            except Exception as error:
                failure.append(error)
            finally:
                self.lib.qt_audio_free(c.byref(result))
                finished.set()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        try:
            while not finished.is_set() or not output.empty():
                if cancelled.is_set():
                    break
                try:
                    yield {'rate': 24000, 'raw_pcm': output.get(timeout=.1)}
                except queue.Empty:
                    continue
            if failure:
                raise failure[0]
            elapsed = time.perf_counter()-started
            if measured['samples'] and not cancelled.is_set():
                yield {'metrics': {'first_audio_ms': measured['first_audio_ms'],
                                   'elapsed_ms': elapsed*1000, 'rtf': elapsed/(measured['samples']/24000)}}
        finally:
            cancelled.set() if not finished.is_set() else None
            worker.join(timeout=3)
            if worker.is_alive():
                # A wedged native call must never keep using the context after
                # the owning slot is released. This is an isolated optional worker.
                os._exit(70)

    def close(self):
        if self.handle:
            if getattr(self,'voice_reference',None) and hasattr(self.lib,'qt_voice_ref_free'):
                self.lib.qt_voice_ref_free(c.byref(self.voice_reference))
            self.lib.qt_free(self.handle)
            self.handle = None


class ProgressiveParakeet:
    """Cache confirmed sentences, repeatedly decode only the unfixed audio tail.

    Parakeet TDT here remains an offline model: this is progressive sentence reuse,
    not an advertised native streaming encoder cache. Final audio is authoritative.
    """
    def __init__(self, folder):
        # NumPy's Windows initialization must finish before another thread
        # blocks on stdin. Importing it during the first request can hang.
        import numpy
        import sherpa_onnx
        folder = Path(folder)
        self.model = sherpa_onnx.OfflineRecognizer.from_transducer(
            tokens=str(folder/'tokens.txt'), encoder=str(folder/'encoder.int8.onnx'),
            decoder=str(folder/'decoder.int8.onnx'), joiner=str(folder/'joiner.int8.onnx'),
            model_type='nemo_transducer', num_threads=4, provider='cpu')
        self.reset()

    def reset(self):
        self.key = None
        self.audio = bytearray()
        self.fixed_text = ''
        self.fixed_sample = 0
        self.previous = None

    def transcribe(self, command):
        import numpy as np
        import re
        raw = command['raw_pcm']
        key = command.get('stream_key')
        if key is None:
            self.reset()
            self.audio.extend(raw)
            final = True
        else:
            if key != self.key:
                self.reset()
                self.key = key
            offset = command['offset']
            if offset*2 > len(self.audio):
                raise ValueError('Segment vocal manquant. Répétez votre phrase.')
            del self.audio[offset*2:]
            self.audio.extend(raw)
            final = command['final']
        if len(self.audio) > 28*16000*2:
            raise ValueError('Phrase vocale trop longue.')
        audio = np.frombuffer(self.audio, dtype='<i2').astype(np.float32)/32768
        if self.fixed_sample >= len(audio):
            self.fixed_text = ''; self.fixed_sample = 0
        stream = self.model.create_stream()
        stream.accept_waveform(16000, audio[self.fixed_sample:])
        self.model.decode_stream(stream)
        text = stream.result.text.strip()
        result = (self.fixed_text+' '+text).strip()[:6000]
        # Two identical sentence observations plus timestamps are needed before
        # discarding its audio from future decodes. Never infer time from text size.
        tokens = list(getattr(stream.result, 'tokens', []) or [])
        timestamps = list(getattr(stream.result, 'timestamps', []) or [])
        if not final and len(tokens) == len(timestamps) and tokens:
            sentence = re.match(r'^(.+[.!?])\s+\S', text)
            if sentence and self.previous and self.previous[0] == sentence[1]:
                stop = None
                built = ''
                for token, stamp in zip(tokens, timestamps):
                    built += token.replace('▁', ' ')
                    if built.strip().endswith(('.', '!', '?')) and built.strip() == sentence[1]:
                        stop = float(stamp)
                        break
                if stop is not None and stop > 0:
                    end = self.fixed_sample+int((stop+.08)*16000)
                    if end < len(audio)-16000:
                        self.fixed_text = (self.fixed_text+' '+sentence[1]).strip()
                        self.fixed_sample = end
                        self.previous = None
            elif sentence:
                self.previous = (sentence[1],)
        if final:
            self.reset()
        return result
