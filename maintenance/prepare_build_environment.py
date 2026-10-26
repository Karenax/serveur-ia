"""Prepare the isolated Windows builder; application runtimes stay build-tool free."""
from pathlib import Path
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    uv=Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
    target=ROOT/'toolchain/build-python'
    python=target/'Scripts/python.exe'
    if not python.is_file():
        subprocess.run([str(uv),'venv','--python',str(ROOT/'Strata-src/.venv/Scripts/python.exe'),str(target)],check=True)
    lock=ROOT/'dependances/verrous/construction-windows.requirements.txt'
    if lock.is_file():
        subprocess.run([str(uv),'pip','install','--python',str(python),'--require-hashes','-r',str(lock)],check=True)
    else:
        subprocess.run([str(uv),'pip','install','--python',str(python),'-r',str(ROOT/'client-qwen/requirements-build.txt'),
                        'setuptools==84.2.1','wheel==0.48.0','pip==26.2.2'],check=True)
    subprocess.run([str(uv),'pip','install','--python',str(python),'--no-build-isolation','-e',str(ROOT/'shared')],check=True)
    subprocess.run([str(uv),'pip','check','--python',str(python)],check=True)
    print('Builder ready:',python)


if __name__=='__main__':main()
