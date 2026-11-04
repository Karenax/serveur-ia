// Exercise the ported upstream GGUF parser and threaded stager with fictitious data.
#include "gguf.hpp"
#include "win32_io.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("fixture path required");
        fnx::Gguf file(argv[1]);
        const auto& tensor = file.t("test.weight");
        if (tensor.nbytes == 0 || tensor.nbytes % sizeof(float)) throw std::runtime_error("wrong tensor size");
        uint64_t overflow = 0;
        if (!fnx_mul_overflow(UINT64_MAX, 2ULL, &overflow) ||
            !fnx_add_overflow(UINT64_MAX, 1ULL, &overflow) ||
            fnx_mul_overflow(32ULL, 2ULL, &overflow) || overflow != 64)
            throw std::runtime_error("overflow guards differ");
        const size_t count = tensor.nbytes / sizeof(float);
        const float* direct = (const float*)tensor.data;
        for (size_t i=0;i<count;++i) if (direct[i] != (float)(i % 997)) throw std::runtime_error("mapped data differs");
        fnx::Stager staged(file, {{{"test.weight"}, false}}, 1, 1);
        const float* read = (const float*)staged.t(0, "test.weight").data;
        for (size_t i=0;i<count;++i) if (read[i] != (float)(i % 997)) throw std::runtime_error("staged data differs");
        staged.done(0);
        std::printf("PASS: upstream GGUF mapping and threaded staged reads on Windows (%zu floats), overflow guards\n", count);
        return 0;
    } catch(const std::exception& error) { std::fprintf(stderr,"%s\n",error.what()); return 1; }
}
