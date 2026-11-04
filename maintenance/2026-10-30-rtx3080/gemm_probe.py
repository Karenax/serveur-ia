"""Small BF16 cuBLAS product on RTX 3080, independently of the model."""
import ctypes as c
import json
import os
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ['CUDA_VISIBLE_DEVICES'] = 'GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f' + (',GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142' if '--peers' in sys.argv else '')
os.environ['CUDA_DISABLE_PTX_JIT'] = '1'
folder = Path(sys.argv[1]).resolve()
os.add_dll_directory(str(folder))
runtime = c.WinDLL(str(ROOT / 'dependances/strata-0.1.45.3/engine-cuda12/cudart64_12.dll'))
lt = c.WinDLL(str(folder / 'cublasLt64_12.dll'))
blas = c.WinDLL(str(folder / 'cublas64_12.dll'))
if '--peers' in sys.argv:
    for device in (1, 2, 0):
        assert runtime.cudaSetDevice(device) == 0
        assert runtime.cudaFree(c.c_void_p()) == 0
handle = c.c_void_p()
status = blas.cublasCreate_v2(c.byref(handle))
assert status == 0, status
buffers = [c.c_void_p() for _ in range(3)]
try:
    dims = [int(value) for value in sys.argv[2:] if value.lstrip('-').isdigit()]
    n, t, k, algorithm = dims if dims else [32, 32, 32, -1]
    for pointer, size in zip(buffers, [2*n*k, 2*k*t, 4*n*t]):
        assert runtime.cudaMalloc(c.byref(pointer), size) == 0
    for pointer, count in zip(buffers[:2], [n*k, k*t]):
        ones = np.full(count, 0x3f80, dtype=np.uint16)
        assert runtime.cudaMemcpy(pointer, c.c_void_p(ones.ctypes.data), 2*count, 1) == 0
    a, b = c.c_float(1), c.c_float(0)
    blas.cublasGemmEx.argtypes = [c.c_void_p, c.c_int, c.c_int, c.c_int, c.c_int, c.c_int,
                                  c.c_void_p, c.c_void_p, c.c_int, c.c_int, c.c_void_p, c.c_int,
                                  c.c_int, c.c_void_p, c.c_void_p, c.c_int, c.c_int, c.c_int, c.c_int]
    status = blas.cublasGemmEx(handle, 1, 0, n, t, k, c.byref(a), buffers[0], 14, k,
                              buffers[1], 14, k, c.byref(b), buffers[2], 0, n, 68, algorithm)
    output = np.empty(n*t, dtype=np.float32)
    copy_status = runtime.cudaMemcpy(c.c_void_p(output.ctypes.data), buffers[2], 4*n*t, 2) if status == 0 else None
    report = {'lib_dir': str(folder), 'cublas_status': status, 'copy_status': copy_status,
              'shape_n_t_k': [n,t,k], 'algorithm': algorithm,
              'correct': status == 0 and copy_status == 0 and bool(np.all(output == k))}
    print(json.dumps(report), flush=True)
finally:
    for pointer in buffers:
        runtime.cudaFree(pointer)
    blas.cublasDestroy_v2(handle)
