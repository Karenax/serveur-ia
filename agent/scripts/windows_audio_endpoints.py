"""Read-only MMDevice endpoint state; never activates an audio client or stream.

ABI: Microsoft's mmdeviceapi.h and IPropertyStore. Keep endpoint IDs opaque.
Only the selected endpoint is monitored; Windows default changes cannot switch it.
"""

import ctypes as ct
from dataclasses import dataclass
import os
from uuid import UUID


ACTIVE = 1


class _Guid(ct.Structure):
    _fields_ = [("data1", ct.c_uint32), ("data2", ct.c_uint16),
                ("data3", ct.c_uint16), ("data4", ct.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(UUID(value).bytes_le)


class _PropertyKey(ct.Structure):
    _fields_ = [("fmtid", _Guid), ("pid", ct.c_uint32)]


class _VariantValue(ct.Union):
    _fields_ = [("pointer", ct.c_void_p), ("space", ct.c_uint64 * 2)]


class _PropVariant(ct.Structure):
    _fields_ = [("vt", ct.c_uint16), ("reserved", ct.c_uint16 * 3),
                ("value", _VariantValue)]


def _method(pointer, index, *argument_types, result=ct.c_int32):
    table = ct.cast(pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
    return ct.WINFUNCTYPE(result, ct.c_void_p, *argument_types)(table[index])


def _checked(result):
    if result < 0:
        raise OSError(f"État audio Windows inaccessible (HRESULT 0x{result & 0xffffffff:08x})")


def _release(pointer):
    if pointer:
        _method(pointer, 2, result=ct.c_uint32)(pointer)


class EndpointApi:
    """One COM apartment lifetime on the calling capture thread."""

    def __init__(self):
        if os.name != "nt":
            raise OSError("Les périphériques MMDevice nécessitent Windows")
        self.ole = ct.WinDLL("ole32")
        self.ole.CoInitializeEx.argtypes = [ct.c_void_p, ct.c_uint32]
        self.ole.CoInitializeEx.restype = ct.c_int32
        self.ole.CoUninitialize.argtypes = []
        self.ole.CoUninitialize.restype = None
        self.ole.CoCreateInstance.argtypes = [ct.POINTER(_Guid), ct.c_void_p,
            ct.c_uint32, ct.POINTER(_Guid), ct.POINTER(ct.c_void_p)]
        self.ole.CoCreateInstance.restype = ct.c_int32
        self.ole.CoTaskMemFree.argtypes = [ct.c_void_p]
        self.ole.CoTaskMemFree.restype = None
        self.ole.PropVariantClear.argtypes = [ct.POINTER(_PropVariant)]
        self.ole.PropVariantClear.restype = ct.c_int32
        self.enumerator = ct.c_void_p()
        result = self.ole.CoInitializeEx(None, 0)
        self.initialized = result in (0, 1)
        # An existing STA apartment remains usable; it belongs to its caller.
        if result & 0xffffffff != 0x80010106:
            _checked(result)
        try:
            clsid = _Guid.parse("bcde0395-e52f-467c-8e3d-c4579291692e")
            iid = _Guid.parse("a95664d2-9614-4f35-a746-de8db63617e6")
            _checked(self.ole.CoCreateInstance(ct.byref(clsid), None, 1,
                ct.byref(iid), ct.byref(self.enumerator)))
        except BaseException:
            self.close()
            raise

    def close(self):
        _release(self.enumerator)
        self.enumerator = ct.c_void_p()
        if self.initialized:
            self.ole.CoUninitialize()
            self.initialized = False

    def _describe(self, device):
        allocated, store = ct.c_void_p(), ct.c_void_p()
        value = _PropVariant()
        try:
            _checked(_method(device, 5, ct.POINTER(ct.c_void_p))(
                device, ct.byref(allocated)))
            endpoint_id = ct.wstring_at(allocated)
            _checked(_method(device, 4, ct.c_uint32, ct.POINTER(ct.c_void_p))(
                device, 0, ct.byref(store)))
            key = _PropertyKey(_Guid.parse("a45c254e-df1c-4efd-8020-67d146a850e0"), 14)
            _checked(_method(store, 5, ct.POINTER(_PropertyKey), ct.POINTER(_PropVariant))(
                store, ct.byref(key), ct.byref(value)))
            if value.vt != 31 or not value.value.pointer:
                raise OSError("Nom du périphérique audio Windows indisponible")
            return {"id": endpoint_id, "name": ct.wstring_at(value.value.pointer)}
        finally:
            self.ole.PropVariantClear(ct.byref(value))
            self.ole.CoTaskMemFree(allocated)
            _release(store)

    def enumerate(self, flow):
        collection = ct.c_void_p()
        rows = []
        try:
            _checked(_method(self.enumerator, 3, ct.c_int32, ct.c_uint32,
                ct.POINTER(ct.c_void_p))(self.enumerator, flow, ACTIVE,
                    ct.byref(collection)))
            count = ct.c_uint32()
            _checked(_method(collection, 3, ct.POINTER(ct.c_uint32))(
                collection, ct.byref(count)))
            for index in range(count.value):
                device = ct.c_void_p()
                try:
                    _checked(_method(collection, 4, ct.c_uint32, ct.POINTER(ct.c_void_p))(
                        collection, index, ct.byref(device)))
                    rows.append(self._describe(device))
                finally:
                    _release(device)
            return rows
        finally:
            _release(collection)

    def state(self, endpoint_id):
        device = ct.c_void_p()
        try:
            _checked(_method(self.enumerator, 5, ct.c_wchar_p, ct.POINTER(ct.c_void_p))(
                self.enumerator, endpoint_id, ct.byref(device)))
            state = ct.c_uint32()
            _checked(_method(device, 6, ct.POINTER(ct.c_uint32))(
                device, ct.byref(state)))
            return state.value
        finally:
            _release(device)


@dataclass(frozen=True)
class SelectedEndpoint:
    track: str
    endpoint_id: str
    name: str


class EndpointMonitor:
    """Bind by exact selected name once; check the same opaque endpoint ID later."""

    def __init__(self, api=None):
        self.api = api if api is not None else EndpointApi()
        self.selected = []
        self.next_check = 0.0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_exception):
        self.close()

    def bind(self, track, name):
        if self.closed:
            raise RuntimeError("Contrôle des périphériques déjà fermé")
        if track not in {"mic", "system"}:
            raise ValueError("Piste audio Windows inconnue")
        wanted = name.removesuffix(" [Loopback]") if track == "system" else name
        matches = [row for row in self.api.enumerate(0 if track == "system" else 1)
                   if row["name"] == wanted]
        if len(matches) != 1:
            raise ValueError(f"Périphérique audio Windows absent ou ambigu : {wanted}")
        self.selected.append(SelectedEndpoint(track, matches[0]["id"], wanted))

    def check(self, now, *, force=False):
        if self.closed:
            raise RuntimeError("Contrôle des périphériques déjà fermé")
        if not force and now < self.next_check:
            return
        for selected in self.selected:
            try:
                active = self.api.state(selected.endpoint_id) == ACTIVE
            except OSError as exc:
                raise ValueError(
                    f"Périphérique audio Windows déconnecté ou inaccessible : {selected.name}"
                ) from exc
            if not active:
                raise ValueError(f"Périphérique audio Windows déconnecté : {selected.name}")
        self.next_check = now + 1.0

    def close(self):
        if not self.closed:
            self.closed = True
            self.api.close()
