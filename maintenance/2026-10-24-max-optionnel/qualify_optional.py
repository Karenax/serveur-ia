"""Real optional-pack download into an isolated QA home; no production runtime changes."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'client-qwen'), str(ROOT/'lanceur')]
from advanced_voice import AdvancedVoice
from max_installation import MaxInstallation
from signing import public


class LocalRelease:
    profile = {'update_public_key': public(ROOT/'lanceur', create=False)}
    def open(self, path):
        if path == '/v1/voice/max/package':
            return (ROOT/'toolchain/voice-max-release/release.json').open('rb')
        if path == '/v1/voice/max/package/download':
            return (ROOT/'toolchain/voice-max-release/runtime.zip').open('rb')
        raise ValueError('Unexpected QA endpoint')


def main():
    home = ROOT/'toolchain/voice-max-optional-qa'
    runtime = AdvancedVoice(home)
    installer = MaxInstallation(home, LocalRelease(), runtime, ROOT/'toolchain/asr-models')
    try:
        installer.detect()
        plan = installer.plan()
        Path(__file__).with_name('download-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(plan, ensure_ascii=False), flush=True)
        installer.install(plan['plan'])
        while installer.thread.is_alive():
            installer.thread.join(10)
            print(json.dumps(installer.status(), ensure_ascii=False), flush=True)
        report = {'installation': installer.status(), 'runtime': runtime.status()}
        Path(__file__).with_name('native-installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if report['installation']['phase'] not in ('ready', 'limited'):
            raise ValueError(report['installation']['message'])
    finally:
        installer.close(); runtime.close()


if __name__ == '__main__':main()
