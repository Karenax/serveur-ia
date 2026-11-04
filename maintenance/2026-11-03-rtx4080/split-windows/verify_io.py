"""Generate fictitious GGUFs and exercise the Windows-ported upstream reader."""
from array import array
import json
from pathlib import Path
import struct
import subprocess

HERE = Path(__file__).resolve().parent


def fixture(name, count):
    tensor = b'test.weight'
    header = struct.pack('<IIQQ', 0x46554747, 3, 1, 0)
    header += struct.pack('<Q', len(tensor)) + tensor + struct.pack('<IQQIQ', 2, 32, count // 32, 0, 0)
    header += b'\0' * ((-len(header)) % 32)
    cycle = array('f', (float(i) for i in range(997)))
    data = cycle * (count // 997) + cycle[:count % 997]
    with (HERE / name).open('wb') as output:
        output.write(header)
        data.tofile(output)


def main():
    fixture('fixture.gguf', 64)
    fixture('fixture-large.gguf', 8 * 2**20)
    (HERE / 'fixture-invalid.gguf').write_bytes(b'bad!' + b'\0' * 92)
    results = []
    for name, expected in [('fixture.gguf', 0), ('fixture-large.gguf', 0), ('fixture-invalid.gguf', 1)]:
        proc = subprocess.run([str(HERE / 'gguf-smoke.exe'), str(HERE / name)],
                              capture_output=True, text=True, timeout=30)
        results.append({'fixture': name, 'bytes': (HERE / name).stat().st_size,
                        'returncode': proc.returncode, 'expected_returncode': expected,
                        'passed': proc.returncode == expected, 'stdout': proc.stdout, 'stderr': proc.stderr})
    (HERE / 'io-validation.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))
    if not all(row['passed'] for row in results):
        raise RuntimeError('Windows GGUF validation failed')


if __name__ == '__main__':
    main()
