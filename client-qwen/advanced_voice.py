"""Optional, measured Voxtral/Qwen-TTS runtime; no model downloads during a call."""
from __future__ import annotations
import base64
from array import array
import hashlib
import json
from pathlib import Path
import os
import queue
import re
import secrets
import subprocess
import threading
import time

MAX_PCM_BYTES = 28 * 16000 * 2


def audio_request(value):
    if not isinstance(value, dict) or set(value)-{'pcm', 'rate', 'request_id', 'utterance', 'offset', 'final'} or value.get('rate') != 16000:
        raise ValueError('Son vocal invalide : PCM mono 16 kHz attendu.')
    if 'request_id' in value and (not isinstance(value['request_id'],str) or not re.fullmatch('[a-f0-9]{32}',value['request_id'])):
        raise ValueError('Identifiant vocal invalide.')
    if any(key in value for key in ('utterance', 'offset', 'final')):
        if (not isinstance(value.get('utterance'), str) or not re.fullmatch('[a-f0-9]{32}', value['utterance']) or
                type(value.get('offset')) is not int or not 0 <= value['offset'] < MAX_PCM_BYTES//2 or type(value.get('final')) is not bool):
            raise ValueError('Segment vocal progressif invalide.')
    encoded = value.get('pcm')
    if not isinstance(encoded, str) or not 1 <= len(encoded) <= (MAX_PCM_BYTES + 2) // 3 * 4:
        raise ValueError('Phrase vocale limitée à 28 secondes.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Son vocal illisible.') from error
    if not raw or len(raw) % 2 or len(raw) > MAX_PCM_BYTES:
        raise ValueError('Son vocal incomplet ou trop long.')
    if value.get('offset', 0)*2 + len(raw) > MAX_PCM_BYTES:
        raise ValueError('Phrase vocale limitée à 28 secondes.')
    return raw


def choose_execution(local, server, requested='auto'):
    if requested not in ('auto', 'pc', 'server'):
        raise ValueError('Lieu du traitement vocal invalide.')
    candidates = [(place, status) for place, status in (('pc', local), ('server', server))
                  if status.get('available') is True and status.get('busy') is not True]
    if requested != 'auto':
        candidates = [item for item in candidates if item[0] == requested]
    if not candidates:
        raise ValueError('Max n’est pas installé ou une opération est en cours ici. Vérifiez son installation ou choisissez Low.')
    # Server latency is measured through the authenticated round trip by the client.
    def rank(item):
        status=item[1];latency=status.get('latency_ms')
        failure=not status.get('loaded') and bool(status.get('runtime_error') or status.get('error_code')=='gpu_unavailable')
        return (failure,latency if type(latency) in (int,float) and latency>0 else float('inf'))
    return min(candidates,key=rank)[0]


class AdvancedVoice:
    def __init__(self, home):
        self.home = Path(home)
        self.lock = threading.RLock()
        self.write_lock = threading.Lock()
        self.slots = {'asr': threading.Lock(), 'tts': threading.Lock()}
        self.processes = {}
        self.current = {}
        self.ready = {'asr': threading.Event(), 'tts': threading.Event()}
        self.error = ''
        self.testing = False
        self.test_message = ''
        self.test_thread = None
        self.closed = False
        self.maintenance = False
        self.error_code = ''
        self.device_info = {}
        self.probing = False
        self.gpu_inventory = {'checked':False,'cards':[],'recommended':None,'error':''}
        self.gpu_inventory_pack = None
        self.gpu_loaded_selection = None
        self.leases = {}
        self.fingerprint_cache = None

    def paths(self):
        configuration = self.configuration()
        if configuration.get('format') == 2:
            root = Path(configuration.get('root', ''))
            native='kiara-asr.dll' if configuration.get('catalogue',{}).get('runtime_api',0)>=6 else 'qwen.dll'
            return (root/'max-worker.exe', root/'native'/native, self.home/'runtime.json', root/'max-worker.exe')
        return (self.home/'python/Scripts/python.exe', self.home/'worker.py', self.home/'runtime.json',
                self.home/'tts-python/Scripts/python.exe')

    def configuration(self):
        try:
            value = json.loads((self.home/'runtime.json').read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def gpu_selection(self):
        try:
            value=json.loads((self.home/'gpu.json').read_text(encoding='utf-8'))['device']
            return value if value=='auto' or isinstance(value,str) and re.fullmatch('[a-f0-9]{24}',value) else 'auto'
        except (OSError,ValueError,KeyError,TypeError):return 'auto'

    def gpu_engine(self):
        configuration=self.configuration()
        return 'asr' if configuration.get('catalogue',{}).get('runtime_api',0)>=6 else 'tts'

    def gpu_status(self,configuration,installed):
        inventory=self.gpu_inventory if self.gpu_inventory_pack==configuration.get('root') else {'checked':False,'cards':[],'recommended':None,'error':''}
        return {**inventory,'selection':self.gpu_selection(),'scanning':self.probing,
                'supported':installed and configuration.get('format')==2 and configuration.get('catalogue',{}).get('runtime_api',0)>=4}

    def native_command(self,engine=None):
        """Same integrity boundary for discovery and inference; probing skips model weights."""
        configuration=self.configuration();root=Path(configuration['root']).resolve()
        if not root.is_relative_to(self.home.resolve()):raise ValueError('Dossier du complément Max invalide.')
        from max_installation import matches,relative_path,safe_directory
        safe_directory(self.home,Path(configuration['root']))
        models={item['name'] for item in configuration.get('catalogue',{}).get('models',[])}
        for name,expected in configuration['manifest'].items():
            if engine is None and (name in models or name.startswith(('asr/','tts/'))):continue
            if engine=='asr' and name.startswith('tts/') or engine=='tts' and name.startswith('asr/'):continue
            relative_path(name);safe_directory(self.home,(root/name).parent)
            if not matches(root/name,expected):raise ValueError('Complément Max incomplet ou corrompu. Réinstallez-le depuis Vocal.')
        command=[str(root/'max-worker.exe'),'--config',str(self.home/'runtime.json')]
        if engine is None:return command+['--probe-gpus']
        command+=['--engine',engine]
        if engine==self.gpu_engine():
            if configuration.get('catalogue',{}).get('runtime_api',0)>=4:command+=['--gpu',self.gpu_selection()]
            elif self.gpu_selection()!='auto':raise ValueError('Mettez le complément Max à jour pour utiliser la carte choisie.')
        return command

    def detect_devices(self):
        if not self.gpu_status(self.configuration(),self.status()['installed'])['supported']:
            raise ValueError('Mettez le complément Max à jour pour détecter les cartes graphiques.')
        self.begin_maintenance();self.probing=True
        try:
            result=subprocess.run(self.native_command(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                text=True,encoding='utf-8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode or not result.stdout or len(result.stdout)>65536:raise ValueError('Détection des cartes impossible. Vérifiez le pilote graphique et réessayez.')
            value=json.loads(result.stdout.strip().splitlines()[-1])
            if value.get('error'):raise ValueError(str(value['error'])[:400])
            cards=value.get('devices')
            if not isinstance(cards,list) or len(cards)>32:raise ValueError('Liste des cartes graphiques invalide.')
            for card in cards:
                if (not isinstance(card,dict) or not isinstance(card.get('id'),str) or not re.fullmatch('[a-f0-9]{24}',card['id']) or
                    not isinstance(card.get('name'),str) or not re.fullmatch('Vulkan[0-9]+',card['name']) or
                    not isinstance(card.get('description'),str) or not 1<=len(card['description'])<=200 or
                    card.get('kind') not in ('dedicated','integrated','other') or
                    any(type(card.get(key)) is not int or not 0<=card[key]<=2**50 for key in ('free_bytes','total_bytes'))):
                    raise ValueError('Description de carte graphique invalide.')
            recommended=value.get('recommended')
            if recommended is not None and recommended not in {card['id'] for card in cards}:raise ValueError('Carte recommandée invalide.')
            self.gpu_inventory={'checked':True,'cards':cards,'recommended':recommended,'error':''}
            self.gpu_inventory_pack=self.configuration().get('root')
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            message=str(error) if isinstance(error,ValueError) else 'Détection des cartes impossible. Vérifiez le pilote graphique puis réessayez.'
            self.gpu_inventory={'checked':False,'cards':[],'recommended':None,'error':message}
            self.gpu_inventory_pack=self.configuration().get('root')
            raise ValueError(message) from error
        finally:self.probing=False;self.end_maintenance()
        return self.status()

    def set_gpu(self,selection):
        if not isinstance(selection,str) or selection!='auto' and not re.fullmatch('[a-f0-9]{24}',selection):raise ValueError('Choisissez une carte graphique de la liste.')
        status=self.status();gpu=status['gpu']
        if not gpu['supported']:raise ValueError('Mettez le complément Max à jour pour choisir la carte graphique.')
        if selection!='auto' and (not gpu['checked'] or sum(card['id']==selection for card in gpu['cards'])!=1):raise ValueError('Cette carte n’est plus identifiable. Actualisez les cartes avant de la choisir.')
        self.begin_maintenance()
        try:
            self.unload(self.gpu_engine())
            from file_lock import locked
            from max_installation import safe_directory
            safe_directory(self.home,self.home/'gpu.json')
            with locked(self.home/'gpu-selection'):
                temporary=self.home/'gpu.json.part';safe_directory(self.home,temporary)
                temporary.write_text(json.dumps({'device':selection}),encoding='utf-8');temporary.replace(self.home/'gpu.json')
            self.device_info={};self.error='';self.error_code='';self.fingerprint_cache=None
        finally:self.end_maintenance()
        return self.status()

    def fingerprint(self):
        try:
            paths = tuple(dict.fromkeys((self.paths()[2], *self.paths()[:2])))
            identity = (self.gpu_selection(),tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns, path.stat().st_ctime_ns) for path in paths))
            if self.fingerprint_cache and self.fingerprint_cache[0] == identity:return self.fingerprint_cache[1]
            digest = hashlib.sha256(self.paths()[2].read_bytes())
            digest.update(self.gpu_selection().encode('ascii'))
            for path in dict.fromkeys(self.paths()[:2]):
                with path.open('rb') as source:
                    while block := source.read(1024*1024):digest.update(block)
            result = digest.hexdigest()
            self.fingerprint_cache = (identity, result)
            return result
        except OSError:
            return ''

    def status(self):
        with self.lock:
            self.leases={key:until for key,until in self.leases.items() if until>time.monotonic()}
        installed = all(path.is_file() for path in self.paths())
        with self.lock:
            try:
                report = json.loads((self.home/'benchmark.json').read_text(encoding='utf-8'))
            except (OSError, ValueError):
                report = {}
        if not isinstance(report,dict):report={}
        measured = installed and report.get('fingerprint') == self.fingerprint()
        recommended = measured and report.get('passed') is True
        inconclusive = measured and report.get('passed') is False and (bool(report.get('error')) or report.get('functional') is False)
        performance = 'recommended' if recommended else 'inconclusive' if inconclusive else 'limited' if measured and report.get('passed') is False else 'unmeasured'
        if self.probing:reason='Détection des cartes graphiques…'
        elif self.testing:reason='Test en cours…'
        elif self.maintenance:reason='Configuration de Max en cours…'
        elif not installed:reason='Mode Max non installé'
        elif self.error:reason=self.error
        elif recommended:reason='Max installé · test satisfaisant'
        elif inconclusive and report.get('error_code')=='gpu_unavailable':reason=report['error']
        elif inconclusive:reason='Test non concluant. Vous pouvez utiliser Max ou relancer le test.'
        elif performance=='limited':reason='Test lent. Vous pouvez utiliser Max ; la réponse peut prendre plus de temps.'
        else:reason='Max installé · vous pouvez l’utiliser. Test de performance facultatif.'
        configuration=self.configuration()
        legacy_custom=any(isinstance(item,dict) and 'CustomVoice' in item.get('repo','') for item in configuration.get('models',[]))
        update_recommended=(configuration.get('format')==2 and configuration.get('catalogue',{}).get('runtime_api',0)<6) or legacy_custom
        return {'installed': installed, 'available': installed and not self.closed and not self.testing and not self.maintenance,
                'loaded': all(event.is_set() for event in self.ready.values()),
                'busy': bool(self.current or self.leases or self.maintenance), 'testing': self.testing, 'message': reason,
                'performance':performance,'test_passed':report.get('passed') if measured else None,
                'runtime_error':self.error,'error_code':self.error_code or (report.get('error_code','') if measured else ''),'update_recommended':update_recommended,
                'device':self.device_info or (report.get('device',{}) if measured else {}),
                'device_loaded':self.ready[self.gpu_engine()].is_set(),'gpu':self.gpu_status(configuration,installed),
                'recognizer':'Whisper Turbo · français' if configuration.get('catalogue',{}).get('runtime_api',0)>=6 else 'Parakeet v3 · progressif',
                'latency_ms': report.get('latency_ms') if measured else None, 'asr_rtf': report.get('asr_rtf') if measured else None,
                'tts_rtf': report.get('tts_rtf') if measured else None, 'engine': self.configuration().get('engine', 'Voxtral Realtime + Qwen3-TTS'),
                'progressive': self.configuration().get('format') == 2}

    def warm(self, owner, session):
        if not self.status()['available']:
            raise ValueError('Installez Max et attendez la fin des opérations en cours avant de l’utiliser.')
        if not isinstance(session,str) or not re.fullmatch('[a-f0-9]{32}',session):raise ValueError('Session Max invalide.')
        with self.lock:
            if self.maintenance or self.testing:raise ValueError('Une opération Max est en cours. Réessayez après sa fin.')
            if self.leases and (owner,session) not in self.leases:raise BlockingIOError('Le mode Max est déjà utilisé. Choisissez Low ou attendez la fin de l’appel.')
            gpu_engine=self.gpu_engine()
            refresh_tts=not self.leases and self.processes.get(gpu_engine) and self.configuration().get('catalogue',{}).get('runtime_api',0)>=4 and self.gpu_loaded_selection!=self.gpu_selection()
            if refresh_tts and self.current:raise BlockingIOError('Attendez la fin du traitement Max avant de changer de carte.')
            self.error='';self.error_code=''
            self.leases[(owner,session)]=time.monotonic()+20*60
        if refresh_tts:self.unload(gpu_engine);self.device_info={}
        self.start('asr');self.start('tts')
        return self.status()

    def release(self, owner, session):
        with self.lock:self.leases.pop((owner,session),None)
        return {'released':True}

    def _write(self, value, engine):
        with self.write_lock:
            process = self.processes.get(engine)
            if not process or process.poll() is not None:
                raise OSError('Le moteur Max s’est arrêté. Testez-le à nouveau.')
            process.stdin.write(json.dumps(value, ensure_ascii=False)+'\n')
            process.stdin.flush()

    def start(self, engine):
        with self.lock:
            if self.closed or self.maintenance:
                raise ValueError('Le moteur Max est fermé.')
            if self.processes.get(engine) and self.processes[engine].poll() is None:
                return
            if not self.status()['installed']:
                raise ValueError('Le mode Max n’est pas installé sur cet appareil.')
            asr_python, worker, configuration, tts_python = self.paths()
            python = asr_python if engine == 'asr' else tts_python
            self.ready[engine].clear()
            if self.configuration().get('format') == 2:
                command=self.native_command(engine)
            else:
                command = [str(python), '-X', 'utf8', str(worker), '--config', str(configuration), '--engine', engine]
            process = subprocess.Popen(command,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.processes[engine] = process
            if engine==self.gpu_engine():self.gpu_loaded_selection=self.gpu_selection()
            threading.Thread(target=self._read, args=(process, engine), daemon=True).start()

    def _read(self, process, engine):
        try:
            for line in process.stdout:
                if len(line) > 100000:
                    raise ValueError('Réponse Max trop volumineuse.')
                frame = json.loads(line)
                job=None
                with self.lock:
                    if process is not self.processes.get(engine):
                        return
                    if frame.get('ready'):
                        if engine==self.gpu_engine() and isinstance(frame.get('device'),dict):
                            self.device_info={key:frame['device'][key] for key in ('name','description','free_bytes','total_bytes','id','kind','pci_id') if key in frame['device']}
                        self.ready[engine].set()
                    elif engine in self.current and frame.get('id') == self.current[engine]['id']:
                        job=self.current[engine]
                    elif frame.get('error'):
                        self.error = frame['error']
                        self.error_code = str(frame.get('code',''))[:80]
                if job:
                    # Full phrases can be generated ahead of playback. Apply
                    # backpressure outside the state lock, retaining bounded RAM.
                    while not job['cancel'].is_set() and not self.closed:
                        try:
                            job['queue'].put(frame,timeout=.1)
                            break
                        except queue.Full:
                            continue
                    if frame.get('done') or frame.get('error'):
                        job['finished'].set()
        except (ValueError, OSError):
            pass
        finally:
            with self.lock:
                if process is self.processes.get(engine):
                    self.ready[engine].clear()
                    self.error = self.error or 'Le moteur Max s’est arrêté. Réessayez le test.'
                    if engine in self.current:
                        self.current[engine]['cancel'].set()
                        self.current[engine]['finished'].set()

    def frames(self, owner, action, value, valid=lambda: True, *, testing=False):
        if action == 'transcribe':
            audio_request(value)
        elif action == 'speak':
            if not isinstance(value, dict) or set(value)-{'request_id', 'text', 'stream'}:
                raise ValueError('Paramètres de lecture Max invalides.')
            if not isinstance(value.get('text'), str) or not 1 <= len(value['text'].strip()) <= 600:
                raise ValueError('Texte vocal limité à 600 caractères.')
            if not isinstance(value.get('request_id'), str) or not re.fullmatch('[a-f0-9]{32}', value['request_id']):
                raise ValueError('Identifiant de lecture invalide.')
        else:
            raise ValueError('Commande Max invalide.')
        if not valid():
            raise PermissionError('Accès vocal désactivé.')
        if not testing and not self.status()['available']:
            raise ValueError(self.status()['message'] + '. Choisissez Low ou relancez le test.')
        if not testing and self.leases and all(key[0]!=owner for key in self.leases):
            raise BlockingIOError('Le mode Max est déjà utilisé par un autre appel.')
        engine = 'asr' if action == 'transcribe' else 'tts'
        if not self.slots[engine].acquire(blocking=False):
            raise BlockingIOError('Le moteur Max est occupé. Réessayez après la réponse.')
        job = {'owner': owner, 'id': value.get('request_id') or secrets.token_hex(16),
               'engine': 'asr' if action == 'transcribe' else 'tts',
               'queue': queue.Queue(maxsize=64), 'cancel': threading.Event(), 'finished': threading.Event()}
        try:
            self.start(job['engine'])
            deadline = time.monotonic()+180
            while not self.ready[job['engine']].wait(.1):
                if not valid() or self.closed:
                    raise PermissionError('Accès vocal désactivé.')
                if self.error or time.monotonic() > deadline:
                    raise ValueError(self.error or 'Chargement Max trop long. Choisissez Low.')
            with self.lock:
                self.current[engine] = job
            command = {'action': action, 'id': job['id'], **value}
            if action == 'transcribe' and 'utterance' in value:
                command['stream_key'] = hashlib.sha256((owner+'\0'+value['utterance']).encode()).hexdigest()
            self._write(command, engine)
            deadline = time.monotonic()+90
            while not job['cancel'].is_set():
                if not valid():
                    raise PermissionError('Accès vocal désactivé.')
                if time.monotonic() > deadline:
                    raise TimeoutError('Le mode Max est trop lent. Raccrochez puis choisissez Low.')
                try:
                    frame = job['queue'].get(timeout=.2)
                except queue.Empty:
                    if job['finished'].is_set():
                        break
                    continue
                if frame.get('error'):
                    raise ValueError(frame['error'])
                yield frame
                if frame.get('done'):
                    return
            raise ValueError('Traitement Max interrompu.')
        finally:
            # Never release the slot while cancelled inference is still executing.
            if not job['finished'].is_set():
                self.cancel(owner, job['id'])
                if not job['finished'].wait(3):
                    self.unload(engine)
            with self.lock:
                if self.current.get(engine) is job:
                    del self.current[engine]
            self.slots[engine].release()

    def transcribe(self, owner, value, valid=lambda: True):
        text = ''
        for frame in self.frames(owner, 'transcribe', value, valid):
            if 'text' in frame:
                text = frame['text']
        if not valid():
            raise PermissionError('Accès vocal désactivé.')
        return {'text': text}

    def cancel(self, owner, identifier):
        with self.lock:
            for engine, job in self.current.items():
                if job['owner'] == owner and job['id'] == identifier:
                    job['cancel'].set()
                    try:
                        self._write({'action': 'cancel', 'id': identifier},engine)
                    except OSError:
                        pass
        return {'cancelled': True}

    def test(self):
        self.status()
        with self.lock:
            if self.closed or self.maintenance or self.testing or self.current or self.leases:
                raise ValueError('Attendez la fin du traitement vocal avant le test.')
            if not self.status()['installed']:
                raise ValueError('Installez le moteur Max avant de le tester.')
            self.save_report({'fingerprint':self.fingerprint(),'passed':False,'error':'Test Max non terminé. Relancez le test.'})
            self.testing = True
            self.test_message = ''
        def run():
            try:
                self.error = '';self.error_code=''
                self.start('asr');self.start('tts')
                deadline=time.monotonic()+180
                while not all(event.is_set() for event in self.ready.values()):
                    if self.closed or self.error or time.monotonic()>deadline:
                        raise ValueError(self.error or 'Le chargement a dépassé la durée du test. Vous pouvez réessayer Max.')
                    time.sleep(.1)
                output = bytearray(); speech_metrics = {}; recognition_metrics = {}; recognized = ''
                for frame in self.frames('benchmark', 'speak', {'request_id': secrets.token_hex(16),
                        'text': 'Bonjour. La réunion du projet Orion est prévue demain à quinze heures.'}, testing=True):
                    if frame.get('pcm'):
                        output.extend(base64.b64decode(frame['pcm'], validate=True))
                    if frame.get('metrics'):
                        speech_metrics = frame['metrics']
                samples = array('h'); samples.frombytes(output)
                if len(samples) < 2400 or len(samples) > 28*24000:
                    raise ValueError('Le test Max n’a pas produit un extrait vocal valide.')
                # Benchmark only: bounded nearest-neighbour resampling, no user audio.
                converted = array('h', (samples[min(len(samples)-1, int(i*1.5))] for i in range(len(samples)*2//3)))
                for frame in self.frames('benchmark', 'transcribe', {'pcm': base64.b64encode(converted.tobytes()).decode(), 'rate': 16000}, testing=True):
                    if frame.get('text'):
                        recognized = frame['text']
                    if frame.get('metrics'):
                        recognition_metrics = frame['metrics']
                first_audio=speech_metrics.get('first_audio_ms');asr_ms=recognition_metrics.get('elapsed_ms')
                latency=first_audio+asr_ms if type(first_audio) in (int,float) and type(asr_ms) in (int,float) else None
                report = {'asr_rtf': recognition_metrics.get('rtf'), 'tts_rtf': speech_metrics.get('rtf'),
                          'first_audio_ms':first_audio,'asr_ms':asr_ms,'latency_ms':latency}
                report['fingerprint'] = self.fingerprint()
                report['functional'] = 'orion' in recognized.casefold() and any(word in recognized.casefold() for word in ('quinze','15'))
                report['device'] = dict(self.device_info)
                report['passed'] = (type(report.get('asr_rtf')) in (int, float) and 0 < report['asr_rtf'] <= .8 and
                                    type(report.get('tts_rtf')) in (int, float) and 0 < report['tts_rtf'] <= .8 and
                                    type(report.get('latency_ms')) in (int, float) and 0 < report['latency_ms'] <= 3000 and
                                    report['functional'])
                self.save_report(report)
                self.test_message = 'Test satisfaisant' if report['passed'] else 'Test lent ou non concluant. Vous pouvez utiliser Max.'
            except (ValueError, OSError, PermissionError) as error:
                self.error = 'Le test Max a échoué. Vérifiez son installation et réessayez.' if isinstance(error,OSError) else str(error)
                try:self.save_report({'fingerprint':self.fingerprint(),'passed':False,'error':self.error,'error_code':self.error_code})
                except OSError:pass
            finally:
                self.testing = False
        self.test_thread = threading.Thread(target=run, daemon=True)
        self.test_thread.start()
        return self.status()

    def save_report(self,report):
        with self.lock:
            temporary=self.home/'benchmark.json.part'
            temporary.write_text(json.dumps(report),encoding='utf-8')
            for attempt in range(6):
                try:
                    temporary.replace(self.home/'benchmark.json')
                    return
                except PermissionError:
                    if attempt==5:raise
                    time.sleep(.02*(attempt+1))

    def unload(self, engine=None):
        with self.lock:
            names = [engine] if engine else list(self.processes)
            processes = [self.processes.pop(name) for name in names if name in self.processes]
            for name in names:
                self.ready[name].clear()
            if self.gpu_engine() in names:self.gpu_loaded_selection=None
        for process in processes:
            if process.poll() is None:
                with self.write_lock:
                    if process.stdin and not process.stdin.closed:process.stdin.close()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    else:process.terminate()
                    process.wait(timeout=5)
            for pipe in (process.stdin, process.stdout):
                if pipe:
                    pipe.close()

    def begin_maintenance(self):
        self.status()
        with self.lock:
            if self.closed or self.maintenance or self.testing or self.current or self.leases or any(slot.locked() for slot in self.slots.values()):
                raise ValueError('Raccrochez et attendez la fin des traitements Max avant de modifier sa configuration.')
            self.maintenance=True

    def end_maintenance(self, removed=False):
        with self.lock:
            self.maintenance=False
            if removed:self.error='';self.error_code='';self.test_message='';self.fingerprint_cache=None;self.device_info={};self.gpu_inventory_pack=None;self.gpu_inventory={'checked':False,'cards':[],'recommended':None,'error':''}

    def close(self):
        self.closed = True
        with self.lock:
            for job in self.current.values():
                job['cancel'].set();job['finished'].set()
        self.unload()
