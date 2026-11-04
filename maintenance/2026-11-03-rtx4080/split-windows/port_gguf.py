"""Apply the experimental IO port only to the isolated source checkout."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = ROOT / 'toolchain/strata-0156-source/src/split/src'
target = source / 'gguf.cpp'
text = target.read_text(encoding='utf-8')
if '#include "win32_io.hpp"' not in text:
    text = text.replace('#include <fcntl.h>\n#include <sys/mman.h>\n#include <sys/stat.h>\n#include <unistd.h>',
                        '#ifdef _WIN32\n#include "win32_io.hpp"\n#else\n#include <fcntl.h>\n#include <sys/mman.h>\n#include <sys/stat.h>\n#include <unistd.h>\n#endif')
    # Keep the original Linux path unchanged. Use named wrappers only in this TU.
    boundary = 'namespace fnx {'
    wrappers = '''#ifdef _WIN32
#define open fnx_open
#define close _close
#define stat _stat64
#define fstat _fstat64
#define O_DIRECT 0x40000000
#define PROT_READ 0
#define MAP_SHARED 0
#define MAP_FAILED ((void*)-1)
#define mmap(a,n,p,f,d,o) fnx_map(d,n)
#define munmap fnx_unmap
#define mincore fnx_mincore
#define posix_memalign fnx_aligned
#define pread fnx_pread
#define __builtin_mul_overflow fnx_mul_overflow
#define __builtin_add_overflow fnx_add_overflow
using ssize_t = int64_t;
#define off_t int64_t
#endif
'''
    text = text.replace(boundary, wrappers + '\n' + boundary, 1)
    text = text.replace('std::free(gr.buf);', '''
#ifdef _WIN32
        _aligned_free(gr.buf);
#else
        std::free(gr.buf);
#endif''')
    text = text.replace('std::free(b);', '''
#ifdef _WIN32
        _aligned_free(b);
#else
        std::free(b);
#endif''')
    target.write_text(text, encoding='utf-8')
shutil.copy2(HERE / 'win32_io.hpp', source / 'win32_io.hpp')
print(target)
