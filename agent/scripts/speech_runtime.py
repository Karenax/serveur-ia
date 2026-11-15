"""Shared optional CUDA profile. Import opens no model, library or device."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import math
import os
from pathlib import Path

CUDA_HANDSHAKE = "agent-speech-cuda-v1"


def device():
    value = os.environ.get("PB_SPEECH_DEVICE", "cpu").strip().lower()
    if value not in {"cpu", "cuda"}:
        raise ValueError("PB_SPEECH_DEVICE doit être cpu ou cuda")
    return value


def profile_key(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in right)
    if isinstance(right, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def cuda_directories(paths=None):
    try:
        paths = json.loads(os.environ.get("PB_SPEECH_CUDA_DLL_DIRS", "[]")) if paths is None else paths
    except ValueError as exc:
        raise ValueError("PB_SPEECH_CUDA_DLL_DIRS doit être une liste JSON de dossiers absolus") from exc
    if not isinstance(paths, list) or len(paths) > 4:
        raise ValueError("Un à quatre dossiers CUDA au maximum sont acceptés")
    result = []
    for value in paths:
        if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
            raise ValueError("Chaque dossier CUDA doit être un chemin absolu existant")
        path = Path(value).resolve(strict=True)
        if not path.is_dir() or os.path.normcase(str(path)) in {os.path.normcase(p) for p in result}:
            raise ValueError("Dossier CUDA absent ou déclaré plusieurs fois")
        result.append(str(path))
    if os.name == "nt":
        required = ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll")
        if not result or any(not any((Path(p) / name).is_file() for p in result) for name in required):
            raise ValueError("Déclarer les dossiers cuBLAS 12 et cuDNN 9 dans PB_SPEECH_CUDA_DLL_DIRS")
    return result


def cuda_profile(config, config_sha256, threads, *, task="live", directories=None):
    if config.get("model") != "medium" or type(threads) is not int or threads != 4:
        raise ValueError("Le profil CUDA audio attend Whisper medium et quatre threads CPU")
    if task not in {"live", "meeting"}:
        raise ValueError("Usage du profil audio inconnu")
    model = Path(config["whisper"])
    if not model.is_absolute():
        raise ValueError("Le modèle CUDA doit être un dossier local absolu")
    directories = cuda_directories(directories)
    # Cheap identities make a DLL replacement invalidate the qualification key.
    # A qualification run must additionally retain the actual loaded DLL hashes.
    libraries = []
    for directory in directories:
        files = sorted(Path(directory).glob("*.dll"))
        if len(files) > 32:
            raise ValueError("Trop de bibliothèques dans un dossier CUDA audio")
        for path in files:
            stat = path.stat()
            libraries.append({"path": str(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    profile = {"runtime": "faster-whisper", "runtime_version": "1.2.1", "ctranslate2_version": "4.8.2",
               "model": "medium", "model_directory": str(model.resolve()), "config_sha256": config_sha256,
               "device": "cuda", "device_index": 0, "compute_type": "int8_float16", "cpu_threads": 4,
               "num_workers": 1, "local_files_only": True, "language": "fr", "beam_size": 5,
               "word_timestamps": True, "vad_filter": True, "previous_text": False,
               "cuda_dll_directories": directories, "cuda_libraries_identity": libraries,
               "task": task, "profile_handshake": CUDA_HANDSHAKE, "contract_revision": 2 if task == "live" else 1}
    if task == "live":
        profile.update(min_silence_ms=250, pcm_context_ms=500, no_speech_threshold=.6,
                       compression_ratio_threshold=2.4)
    else:
        profile.update(diarization_device="cpu", diarization_cpu_threads=4)
    return profile


def configured_cuda_profile(models, *, task="live", directories=None):
    raw = (Path(models) / "models.json").read_bytes()
    config = json.loads(raw)
    threads = int(os.environ.get("PB_SPEECH_THREADS", config.get("cpu_threads", 4)))
    return cuda_profile(config, hashlib.sha256(raw).hexdigest(), threads, task=task, directories=directories)


def child_environment(profile, environment=None):
    """Prefix only this child PATH: CT2's cuBLAS loader uses LoadLibraryA."""
    result = dict(os.environ if environment is None else environment)
    previous = next((v for k, v in result.items() if k.upper() == "PATH"), "")
    result = {k: v for k, v in result.items() if k.upper() != "PATH"}
    prefix = profile["cuda_dll_directories"]
    result["PATH"] = os.pathsep.join([*prefix, previous])
    result["PB_SPEECH_DEVICE"] = "cuda"
    result["PB_SPEECH_CUDA_DLL_DIRS"] = json.dumps(prefix)
    result["PB_SPEECH_THREADS"] = str(profile["cpu_threads"])
    return result


@contextmanager
def cuda_libraries(profile):
    """Register search handles in the isolated worker before importing CT2."""
    original = dict(os.environ)
    handles = ExitStack()
    try:
        updated = child_environment(profile, original)
        for key in tuple(os.environ):
            if key.upper() == "PATH":
                del os.environ[key]
        os.environ["PATH"] = updated["PATH"]
        if os.name == "nt":
            for directory in profile["cuda_dll_directories"]:
                handle = os.add_dll_directory(directory)
                handles.callback(handle.close)
        yield
    finally:
        try:
            handles.close()
        finally:
            for key in tuple(os.environ):
                if key.upper() == "PATH":
                    del os.environ[key]
            os.environ.update({k: v for k, v in original.items() if k.upper() == "PATH"})


def _requested(profile):
    return {"model_directory": profile["model_directory"], "device": "cuda", "device_index": 0,
            "compute_type": "int8_float16", "cpu_threads": 4, "num_workers": 1, "local_files_only": True}


def validate_observation(observation, profile):
    expected = {"requested": _requested(profile),
                "native": {"device": "cuda", "compute_type": "int8_float16", "device_index": [0], "num_workers": 1},
                "versions": {"faster_whisper": "1.2.1", "ctranslate2": "4.8.2"}}
    if not _same(observation, expected):
        raise ValueError("Le moteur audio chargé ne correspond pas au profil CUDA demandé ; aucun repli CPU")


def construct_cuda_model(constructor, profile, fw_version, ct_version):
    if (fw_version, ct_version) != ("1.2.1", "4.8.2"):
        raise ValueError("Versions faster-whisper/CTranslate2 incompatibles avec le profil CUDA audio")
    kwargs = {k: v for k, v in _requested(profile).items() if k != "model_directory"}
    model = constructor(profile["model_directory"], **kwargs)
    native = getattr(model, "model", None)
    observed = {"requested": _requested(profile),
                "native": {key: getattr(native, key, None) for key in ("device", "compute_type", "device_index", "num_workers")},
                "versions": {"faster_whisper": fw_version, "ctranslate2": ct_version}}
    validate_observation(observed, profile)
    return model, observed


def cuda_ready(profile, observed, load_s, offline_guard):
    validate_observation(observed, profile)
    event = {"kind": "ready", "handshake": CUDA_HANDSHAKE, "profile": profile,
             "runtime_profile_key": profile_key(profile), "observed_constructor": observed,
             "load_s": load_s, "offline_guard": offline_guard}
    event.update({k: profile[k] for k in ("model", "cpu_threads", "device", "compute_type", "device_index", "runtime_version")})
    validate_cuda_ready(event, profile)
    return event


def validate_cuda_ready(event, profile):
    if (event.get("kind") != "ready" or event.get("handshake") != CUDA_HANDSHAKE
            or not _same(event.get("profile"), profile) or event.get("runtime_profile_key") != profile_key(profile)
            or any(not _same(event.get(k), profile[k]) for k in ("model", "cpu_threads", "device", "compute_type", "device_index", "runtime_version"))):
        raise ValueError("Le profil complet du sous-processus audio diffère du profil demandé")
    duration = event.get("load_s")
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        raise ValueError("Durée de chargement audio invalide")
    if not isinstance(event.get("offline_guard"), dict):
        raise ValueError("Observation du mode hors ligne audio absente")
    validate_observation(event.get("observed_constructor"), profile)
