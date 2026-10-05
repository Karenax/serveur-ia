"""Build changed C++ units against existing Pascal CUDA libraries, in isolation."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
build = root / 'strata-build-p100'
out = root / 'strata-cache-build-bin'
obj = out / 'obj'
obj.mkdir(parents=True, exist_ok=True)
vc = root / 'toolchain/msvc/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64'
cuda = root / 'toolchain/cuda-12.4'
source = root / 'Strata-src'
ggml = root / 'toolchain/strata-llama/llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d/ggml/include'

def run(args):
    subprocess.run([str(a) for a in args], cwd=build, check=True)

def compile(relative):
    target = obj / (Path(relative).name + '.obj')
    run([vc / 'cl.exe', '/nologo', '/TP', '/std:c++20', '/O2', '/Ob2', '/DNDEBUG', '/MT',
         '/EHsc', '/utf-8', '/Zi', '/W4', '/DWIN32', '/D_WINDOWS', '/DSTRATA_NATIVE_EXPERTS=1',
         '/DSTRATA_PREFILL_MMQ=1', '/DSTRATA_VERSION="0.1.35"',
         '/I' + str(source / 'include'), '/I' + str(cuda / 'include'), '/I' + str(ggml),
         '/Fo' + str(target), '/Fd' + str(obj / 'compiler.pdb'), '/c', source / relative])
    return target

changed = {}
for relative in ['src/core/conversation_state.cpp', 'src/core/conversation_snapshot.cpp']:
    changed[Path(relative).name + '.obj'] = compile(relative)
text = (build / 'build.ninja').read_text(encoding='utf-8')
line = next(line for line in text.splitlines() if line.startswith('build strata_engine.lib:'))
original = line.split(' ||')[0].split()[3:]
objects = [changed.get(Path(p.replace('\\', '/')).name, build / p) for p in original]
engine = out / 'strata_engine.lib'
run([vc / 'lib.exe', '/nologo', '/machine:x64', '/out:' + str(engine), *objects])
libs = [engine, build / 'strata_kernels.lib', build / 'strata_core.lib', build / 'strata_kernels_cpu.lib',
        build / 'ggml/src/ggml-cpu.lib', build / 'ggml/src/ggml-base.lib', cuda / 'lib/x64/cudart.lib',
        'kernel32.lib', 'user32.lib', 'gdi32.lib', 'shell32.lib', 'ole32.lib', 'advapi32.lib']

def link(name, main, extra=()):
    run([vc / 'link.exe', '/nologo', '/machine:x64', '/INCREMENTAL:NO', '/subsystem:console',
         '/DEBUG', '/OPT:REF', '/OPT:ICF', '/out:' + str(out / (name + '.exe')),
         '/pdb:' + str(out / (name + '.pdb')), '/LIBPATH:' + str(cuda / 'lib/x64'), main, *libs, *extra])

for name in ['conversation_snapshot_test', 'conversation_validation_test', 'conversation_cache_test']:
    link(name, compile('src/core/' + name + '.cpp'))
link('strata', compile('src/program/generate.cpp'),
     [build / 'strata_prefill.lib', build / 'strata_spec.lib', build / 'strata_mmq.lib',
      cuda / 'lib/x64/cublas.lib', cuda / 'lib/x64/cublasLt.lib', cuda / 'lib/x64/cudadevrt.lib'])
print('Cache build complete:', out, flush=True)
