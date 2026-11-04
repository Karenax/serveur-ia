"""Verify real P2200 image encoding with the model on F:."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
os.environ['STRATA_VISION_READY_S'] = '45'
sys.path.insert(0, str(ROOT / 'dependances/strata-0.1.43.1/source'))
from serve.server import Vision, child_env, vision_env


def gpu():
    return subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,name,memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                                   text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()


def accelerated(report, text):
    uuid = report['vision']['cuda_device']
    def used(csv):
        return float(next(line.split(',')[2].strip() for line in csv.splitlines() if line.startswith(uuid + ',')))
    return report.get('tokens', 0) > 0 and used(report['loaded']) - used(report['before']) > 256 and 'failed to initialize CUDA' not in text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cuda124', action='store_true')
    parser.add_argument('--tag', help='Distinct report name to preserve previous measurements')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'lanceur/base-strata.json').read_text(encoding='utf-8-sig'))
    cfg['vision']['model'] = 'F:/Qwen3.8-Flash-Next-Uncensored-IQ4_XS-00001-of-00003.gguf'
    if args.cuda124:
        cfg['lib_dirs'] = [str(ROOT / 'toolchain/cuda-12.4/bin'), *cfg.get('lib_dirs', [])]
    tag = args.tag or ('cuda124' if args.cuda124 else 'configured')
    if Path(tag).name != tag or '/' in tag or '\\' in tag:
        parser.error('tag must be a simple filename component')
    if args.tag and any((HERE / f'vision-{tag}.{suffix}').exists() for suffix in ('log', 'json')):
        parser.error('report already exists')
    report = {'before': gpu(), 'vision': cfg['vision'], 'lib_dirs': cfg.get('lib_dirs')}
    encoder = None
    try:
        with (HERE / f'vision-{tag}.log').open('w', encoding='utf-8') as log:
            start = time.monotonic()
            encoder = Vision(cfg['vision'], log, vision_env(cfg, child_env(cfg)))
            report.update(startup_s=time.monotonic() - start, loaded=gpu())
            start = time.monotonic()
            path, tokens = encoder.encode((ROOT / 'maintenance/2026-10-14-vision/vision-fixture.png').read_bytes())
            report.update(encode_s=time.monotonic() - start, tokens=tokens, embedding_bytes=path.stat().st_size, after_encode=gpu())
            log.flush()
            text = (HERE / f'vision-{tag}.log').read_text(encoding='utf-8', errors='replace')
            report['passed'] = accelerated(report, text)
    except Exception as error:
        report.update(error=repr(error), passed=False)
    finally:
        if encoder:
            encoder.shutdown()
        report['after_close'] = gpu()
        (HERE / f'vision-{tag}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
