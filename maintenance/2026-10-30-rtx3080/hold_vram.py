"""Commit a bounded CUDA allocation to check memory coexistence, without compute load."""
import argparse
import ctypes as c
import json
import os
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mib', type=int, required=True)
    parser.add_argument('--report', type=Path, required=True)
    options = parser.parse_args()
    assert 0 < options.mib <= 4096
    os.environ['CUDA_VISIBLE_DEVICES'] = 'GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f'
    folder = Path('F:/Kiara/moteurs/strata-0.1.54-cuda12')
    directory = os.add_dll_directory(str(folder))
    runtime = c.WinDLL(str(folder / 'cudart64_12.dll'))
    runtime.cudaMalloc.argtypes = [c.POINTER(c.c_void_p), c.c_size_t]
    runtime.cudaMemset.argtypes = [c.c_void_p, c.c_int, c.c_size_t]
    runtime.cudaMemGetInfo.argtypes = [c.POINTER(c.c_size_t), c.POINTER(c.c_size_t)]
    runtime.cudaFree.argtypes = [c.c_void_p]
    pointer = c.c_void_p()
    try:
        assert runtime.cudaSetDevice(0) == 0
        size = options.mib * 2**20
        status = runtime.cudaMalloc(c.byref(pointer), size)
        assert status == 0, ('cudaMalloc', status)
        assert runtime.cudaMemset(pointer, 0, size) == 0
        assert runtime.cudaDeviceSynchronize() == 0
        free, total = c.c_size_t(), c.c_size_t()
        assert runtime.cudaMemGetInfo(c.byref(free), c.byref(total)) == 0
        options.report.write_text(json.dumps({'pid': os.getpid(), 'committed_mib': options.mib,
            'cuda_free_mib_after': free.value / 2**20, 'cuda_total_mib': total.value / 2**20,
            'scope': 'Memory allocation only; does not simulate concurrent model compute'}, indent=2) + '\n')
        time.sleep(1800)
    finally:
        if pointer:
            runtime.cudaFree(pointer)
        directory.close()


if __name__ == '__main__':
    main()
