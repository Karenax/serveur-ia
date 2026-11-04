"""Linux desktop storage and explicit capability limits for the shared client."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import struct


def data_home():
    base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))
    if not base.is_absolute():
        raise ValueError('XDG_DATA_HOME doit être un chemin absolu.')
    directory = base/'kiara'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


@lru_cache(maxsize=1)
def cipher():
    from keyring.backends.SecretService import Keyring
    return _cipher_with_backend(Keyring())  # Never select a plaintext fallback backend.


def _cipher_with_backend(backend):
    from cryptography.fernet import Fernet
    from file_lock import locked
    directory = data_home()
    try:
        with locked(directory/'keyring'):
            key = backend.get_password('Kiara', 'local-data-v1')
            if key is None:
                if any(directory.glob('*.enc')) or any(directory.rglob('*.dpapi')):
                    raise RuntimeError('La clé de vos données est absente du trousseau. Restaurez votre trousseau avant de relancer Kiara.')
                key = Fernet.generate_key().decode('ascii')
                backend.set_password('Kiara', 'local-data-v1', key)
            return Fernet(key.encode('ascii'))
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError('Le trousseau est inaccessible. Déverrouillez le trousseau de votre session puis relancez Kiara.') from error


def protect(value, decrypt=False):
    from cryptography.fernet import InvalidToken
    raw = value if isinstance(value, bytes) else value.encode('utf-8')
    try:
        return cipher().decrypt(raw) if decrypt else cipher().encrypt(raw)
    except InvalidToken as error:
        raise ValueError('Données locales illisibles. Le fichier original est conservé.') from error


def settings_path(profile):
    identity = hashlib.sha256((profile['url']+profile['token']).encode()).hexdigest()[:20]
    return data_home()/(identity+'.enc')


def import_profile(path):
    """Read a personal Windows client's bounded JSON footer without executing it."""
    from wg_bridge import validate_profile
    with Path(path).open('rb') as stream:
        stream.seek(0, 2)
        length = stream.tell()
        if length < 17:
            raise ValueError('Choisissez le client personnel fourni par votre administrateur.')
        stream.seek(-16, 2)
        footer = stream.read(16)
        if footer[4:] != b'QWENPROFILE1':
            raise ValueError('Ce fichier ne contient pas d’accès personnel Kiara.')
        size = struct.unpack('<I', footer[:4])[0]
        if not 1 <= size <= 65536 or size > length-16:
            raise ValueError('Accès personnel incomplet ou invalide.')
        stream.seek(-16-size, 2)
        profile = json.loads(stream.read(size))
    validate_profile(profile)
    return profile


def read_profile():
    from history_store import atomic
    from wg_bridge import validate_profile
    path = data_home()/'profile.enc'
    if path.exists():
        profile = json.loads(protect(path.read_bytes(), decrypt=True))
        validate_profile(profile)
        return profile
    # Import the existing personal access rather than inventing a second account.
    from tkinter import Tk, filedialog, messagebox
    root = Tk()
    root.withdraw()
    try:
        messagebox.showinfo('Bienvenue dans Kiara',
            'Choisissez le client personnel fourni par votre administrateur pour activer votre accès Linux.\n\n'
            'Utilisez un accès distinct pour chaque appareil connecté en même temps.', parent=root)
        selected = filedialog.askopenfilename(parent=root, title='Choisir mon accès Kiara',
            filetypes=[('Client personnel Kiara', '*.exe'), ('Tous les fichiers', '*')])
        if not selected:
            raise ValueError('Aucun accès sélectionné. Relancez Kiara pour choisir votre fichier.')
        profile = import_profile(selected)
        atomic(path, protect(json.dumps(profile)))
        return profile
    finally:
        root.destroy()


class UnavailableVoice:
    """The optional local Windows Max pack cannot be installed on Linux."""
    def __init__(self, home):
        self.home = self.cache = Path(home)
        self.value = {'phase':'unavailable', 'session':'', 'quality':'low'}

    def status(self):
        return {**self.value, 'available':False, 'installed':False, 'supported':False,
                'message':'Max sur ce PC est réservé à Windows. Choisissez le serveur Kiara ou Low.',
                'microphone_closed':True, 'model_bytes':0, 'turns':[]}

    def close(self):
        pass

    def configuration(self):
        return {}

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        def unavailable(*args, **kwargs):
            raise ValueError(self.status()['message'])
        return unavailable


def services():
    import sys
    from conversation_service import ConversationService, DictationService
    directory = data_home()/'voice'
    resources = Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'voice'
    return (UnavailableVoice(directory),DictationService(resources,directory/'asr'),
            ConversationService(resources,directory/'asr'),
            ConversationService(resources,mode='wakeword'),UnavailableVoice(directory))
