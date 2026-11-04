// Experimental Windows IO backend for Strata v0.2.10's split GGUF reader.
// Read-only files. This does not implement a full Windows split engine.
#pragma once
#define NOMINMAX
#include <windows.h>
#include <io.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <malloc.h>
#include <cerrno>
#include <cstdint>
#include <limits>
#include <cstring>

inline int fnx_open(const char* path, int flags) {
    // The Linux reader already supports a buffered fallback. Do not claim direct IO.
    if (flags & 0x40000000) { errno = EINVAL; return -1; }
    return _open(path, flags | _O_BINARY);
}
inline void* fnx_map(int fd, size_t bytes) {
    HANDLE mapping = CreateFileMappingW((HANDLE)_get_osfhandle(fd), nullptr, PAGE_READONLY, 0, 0, nullptr);
    if (!mapping) return (void*)-1;
    void* base = MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, bytes);
    CloseHandle(mapping);
    return base ? base : (void*)-1;
}
inline int fnx_unmap(void* base, size_t) { return UnmapViewOfFile(base) ? 0 : -1; }
inline int fnx_mincore(void*, size_t bytes, unsigned char* residency) {
    // Unknown residency: use the existing read path for every page, never skip data.
    std::memset(residency, 0, (bytes + 4095) / 4096);
    return 0;
}
inline int fnx_aligned(void** p, size_t align, size_t bytes) {
    *p = _aligned_malloc(bytes, align);
    return *p ? 0 : ENOMEM;
}
inline int64_t fnx_pread(int fd, void* buffer, size_t bytes, int64_t offset) {
    OVERLAPPED operation{};
    operation.Offset = (DWORD)(uint64_t)offset;
    operation.OffsetHigh = (DWORD)((uint64_t)offset >> 32);
    operation.hEvent = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (!operation.hEvent) { errno = EIO; return -1; }
    DWORD got = 0;
    HANDLE file = (HANDLE)_get_osfhandle(fd);
    BOOL ok = ReadFile(file, buffer, (DWORD)bytes, &got, &operation);
    if (!ok && GetLastError() == ERROR_IO_PENDING)
        ok = GetOverlappedResult(file, &operation, &got, TRUE);
    DWORD error = ok ? ERROR_SUCCESS : GetLastError();
    CloseHandle(operation.hEvent);
    if (!ok && error != ERROR_HANDLE_EOF) { errno = EIO; return -1; }
    return got;
}
template<class A, class B, class R> bool fnx_mul_overflow(A a, B b, R* out) {
    if (b != 0 && a > std::numeric_limits<R>::max() / b) return true;
    *out = (R)a * (R)b;
    return false;
}
template<class A, class B, class R> bool fnx_add_overflow(A a, B b, R* out) {
    if (a > std::numeric_limits<R>::max() - b) return true;
    *out = (R)a + (R)b;
    return false;
}
