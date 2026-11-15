"""Detached, single-instance supervisor for the local Agent backend."""
from __future__ import annotations

import argparse
import contextlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "logs" / "runtime"


@contextlib.contextmanager
def instance_lock(directory: Path):
    """OS lock is released even when the supervisor is forcibly terminated."""
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "supervisor.lock").open("a+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def port_busy(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def write_state(directory: Path, state: dict):
    temporary = directory / f"state-{os.getpid()}.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    # Windows readers may briefly deny replacement of the previous snapshot.
    # Preserve its atomic visibility while allowing those handles to close.
    deadline = time.monotonic() + 5
    while True:
        try:
            temporary.replace(directory / "state.json")
            return
        except PermissionError as error:
            if (os.name != 'nt' or getattr(error, 'winerror', None) not in {5, 32, 33}
                    or time.monotonic() >= deadline):
                raise
            time.sleep(0.01)


def read_state(directory: Path) -> dict:
    try:
        return json.loads((directory / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def restart_delay(failures: int) -> float:
    return min(60, 5 * 2 ** min(max(failures - 1, 0), 4))


def child_environment() -> dict[str, str]:
    env = dict(os.environ)
    # Test conveniences must never silently weaken the canonical launcher.
    env.pop('AGENT_TESTING', None)
    env["MINIPILOT_BRAIN_URL"] = "http://127.0.0.1:8001"
    env.setdefault("AGENT_DOCUMENT_JOBS_ENABLED", "1")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONFAULTHANDLER"] = "1"
    return env


def supervise(command: list[str], *, directory: Path = RUNTIME,
              cwd: Path = ROOT, host: str = "127.0.0.1", port: int = 8001,
              poll_seconds: float = 1) -> int:
    with instance_lock(directory) as acquired:
        if not acquired:
            return 0
        token = uuid.uuid4().hex
        logger = logging.getLogger(f"agent-supervisor-{token}")
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(directory / "supervisor.log", maxBytes=2 * 1024**2,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        state = {"supervisor_pid": os.getpid(), "token": token, "backend_pid": None,
                 "status": "starting", "restarts": 0, "last_exit_code": None}
        stop_file = directory / "stop.json"
        process = None

        def stopping():
            try:
                return json.loads(stop_file.read_text(encoding="utf-8")).get("token") == token
            except (OSError, ValueError):
                return False

        def wait(seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if stopping():
                    return True
                time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
            return stopping()

        write_state(directory, state)
        logger.info("Superviseur démarré ; dossier=%s ; port=%s", cwd, port)
        failures = 0
        try:
            while not stopping():
                # An existing listener is never killed or adopted by this supervisor.
                if port_busy(host, port):
                    state["status"] = "waiting_existing_listener"
                    write_state(directory, state)
                    if wait(poll_seconds):
                        break
                    continue
                try:
                    # Rotate only between launches: the child owns the open log handles.
                    for name in ("backend.out.log", "backend.err.log"):
                        path = directory / name
                        if path.exists() and path.stat().st_size >= 10 * 1024**2:
                            path.replace(directory / f"{name}.previous")
                    with (directory / "backend.out.log").open("ab") as out, \
                            (directory / "backend.err.log").open("ab") as err:
                        process = subprocess.Popen(command, cwd=cwd, env=child_environment(),
                                                   stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                except OSError:
                    logger.exception("Échec du lancement du backend")
                    failures += 1
                else:
                    started = time.monotonic()
                    state.update(backend_pid=process.pid, status="running")
                    write_state(directory, state)
                    logger.info("Backend lancé ; pid=%s", process.pid)
                    while process.poll() is None and not stopping():
                        time.sleep(poll_seconds)
                    if stopping():
                        break
                    state["last_exit_code"] = process.returncode
                    logger.warning("Backend arrêté ; pid=%s ; code=%s", process.pid, process.returncode)
                    failures = 1 if time.monotonic() - started >= 60 else failures + 1
                    process = None
                delay = restart_delay(failures)
                state.update(backend_pid=None, status="restart_wait", retry_seconds=delay)
                state["restarts"] += 1
                write_state(directory, state)
                logger.info("Relance dans %s secondes", delay)
                if wait(delay):
                    break
        finally:
            if process is not None and process.poll() is None:
                logger.info("Arrêt explicite du backend supervisé ; pid=%s", process.pid)
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            state.update(backend_pid=None, status="stopped")
            write_state(directory, state)
            logger.info("Superviseur arrêté")
            handler.close()
            logger.removeHandler(handler)
    return 0


def start() -> int:
    # The lock, rather than a potentially stale PID, is the authority.
    with instance_lock(RUNTIME) as acquired:
        if not acquired:
            print("Le superviseur Agent est déjà actif.")
            return 0
    executable = Path(sys.executable)
    windowless = executable.with_name("pythonw.exe")
    if os.name == "nt" and windowless.is_file():
        executable = windowless
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    command = [str(executable), str(Path(__file__).resolve()), "run"]
    with (RUNTIME / "launcher.err.log").open("ab") as err:
        options = dict(cwd=ROOT, stdin=subprocess.DEVNULL, stdout=err, stderr=err,
                       creationflags=flags, start_new_session=os.name != "nt")
        try:
            child = subprocess.Popen(command, **dict(options, creationflags=flags | (
                subprocess.CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0)))
        except OSError:
            child = subprocess.Popen(command, **options)
    for _ in range(50):
        with instance_lock(RUNTIME) as acquired:
            if not acquired:
                print("Superviseur Agent démarré en arrière-plan.")
                return 0
        if child.poll() is not None:
            break
        time.sleep(0.1)
    print("Le superviseur ne démarre pas ; consulter logs/runtime/launcher.err.log.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "run", "status", "stop"))
    args = parser.parse_args()
    if args.action == "start":
        return start()
    if args.action == "run":
        executable = str(Path(sys.executable).with_name("python.exe")) if os.name == "nt" else sys.executable
        return supervise([executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"])
    with instance_lock(RUNTIME) as acquired:
        state = read_state(RUNTIME)
        if acquired:
            state["status"] = "stopped"
        elif args.action == "stop":
            (RUNTIME / "stop.json").write_text(json.dumps({"token": state.get("token")}), encoding="utf-8")
    if args.action == "stop":
        for _ in range(150):
            with instance_lock(RUNTIME) as acquired:
                if acquired:
                    print("Superviseur Agent arrêté.")
                    return 0
            time.sleep(0.2)
        print("Arrêt encore en cours ; consulter logs/runtime/supervisor.log.")
        return 1
    state["port_open"] = port_busy("127.0.0.1", 8001)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
