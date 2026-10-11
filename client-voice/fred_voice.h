#pragma once
#include <cstdint>
#if defined(_WIN32)
#define FRED_EXPORT __declspec(dllexport)
#else
#define FRED_EXPORT __attribute__((visibility("default")))
#endif
extern "C" {
FRED_EXPORT void* fred_voice_create(const char* model, const char* backends, int threads);
FRED_EXPORT void fred_voice_feed(void* handle, const int16_t* samples, int count);
FRED_EXPORT void fred_voice_stop(void* handle);
FRED_EXPORT void fred_voice_cancel(void* handle);
FRED_EXPORT int fred_voice_status(void* handle, char* output, int capacity);
FRED_EXPORT void fred_voice_destroy(void* handle);
}

