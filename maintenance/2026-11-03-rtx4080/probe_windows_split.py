"""Read-only CUDA prerequisites and bounded host-memory signalling on Windows.

This is a transport prerequisite test, not model inference or a performance test.
"""
import ctypes as c
import json
from pathlib import Path


def main():
    cuda = c.WinDLL('nvcuda.dll')
    ptr = c.c_void_p
    u64 = c.c_uint64

    def bind(name, types):
        fn = getattr(cuda, name)
        fn.argtypes = types
        fn.restype = c.c_int
        return fn

    init = bind('cuInit', [c.c_uint])
    count = bind('cuDeviceGetCount', [c.POINTER(c.c_int)])
    name = bind('cuDeviceGetName', [ptr, c.c_int, c.c_int])
    attribute = bind('cuDeviceGetAttribute', [c.POINTER(c.c_int), c.c_int, c.c_int])
    retain = bind('cuDevicePrimaryCtxRetain', [c.POINTER(ptr), c.c_int])
    release = bind('cuDevicePrimaryCtxRelease_v2', [c.c_int])
    current = bind('cuCtxSetCurrent', [ptr])
    alloc = bind('cuMemHostAlloc', [c.POINTER(ptr), c.c_size_t, c.c_uint])
    free = bind('cuMemFreeHost', [ptr])
    deviceptr = bind('cuMemHostGetDevicePointer_v2', [c.POINTER(u64), ptr, c.c_uint])
    stream_create = bind('cuStreamCreate', [c.POINTER(ptr), c.c_uint])
    stream_destroy = bind('cuStreamDestroy_v2', [ptr])
    write = bind('cuStreamWriteValue32_v2', [ptr, u64, c.c_uint, c.c_uint])
    wait = bind('cuStreamWaitValue32_v2', [ptr, u64, c.c_uint, c.c_uint])
    sync = bind('cuStreamSynchronize', [ptr])
    errorname = bind('cuGetErrorName', [c.c_int, c.POINTER(c.c_char_p)])

    def result(code):
        out = c.c_char_p()
        errorname(code, c.byref(out))
        return {'code': code, 'name': out.value.decode() if out.value else 'unknown'}

    assert init(0) == 0
    n = c.c_int()
    assert count(c.byref(n)) == 0
    report = []
    for dev in range(n.value):
        buf = c.create_string_buffer(256)
        assert name(buf, 256, dev) == 0
        item = {'device': dev, 'name': buf.value.decode(), 'attributes': {}}
        for label, attr in [('cc_major', 75), ('cc_minor', 76), ('mapped_host_memory', 19),
                            ('stream_memops_v1', 92), ('virtual_memory', 102), ('tcc', 35)]:
            value = c.c_int()
            code = attribute(c.byref(value), attr, dev)
            item['attributes'][label] = {'value': value.value, **result(code)}
        ctx = ptr()
        code = retain(c.byref(ctx), dev)
        item['context'] = result(code)
        if code == 0:
            host = ptr()
            stream = ptr()
            try:
                assert current(ctx) == 0
                code = alloc(c.byref(host), 4096, 3)  # PORTABLE | DEVICEMAP
                item['mapped_allocation'] = result(code)
                if code == 0:
                    address = u64()
                    code = deviceptr(c.byref(address), host, 0)
                    item['device_pointer'] = result(code)
                    if code == 0:
                        assert stream_create(c.byref(stream), 1) == 0
                        word = c.c_uint.from_address(host.value)
                        word.value = 0
                        code = write(stream, address, 123, 0)
                        item['stream_write'] = result(code)
                        if code == 0:
                            item['write_sync'] = result(sync(stream))
                            item['written_value'] = word.value
                            # The condition is already true: this wait cannot spin on a missing producer.
                            if word.value == 123:
                                item['stream_wait'] = result(wait(stream, address, 123, 1))
                                item['wait_sync'] = result(sync(stream))
            finally:
                if stream.value:
                    stream_destroy(stream)
                if host.value:
                    free(host)
                current(ptr())
                release(dev)
        report.append(item)
    out = Path(__file__).with_name('windows-split-prerequisites.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
