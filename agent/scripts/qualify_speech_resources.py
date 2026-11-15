"""Model CPU/RAM and prewarmed5s requests, including Windows venv descendants."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.audio_capture import PreparedAudio
from app.services.live_speech import ResidentWhisper, model_fingerprint, speech_profile, speech_profile_key


class ProcessTreeMeter:
    def __init__(self, pid):
        import psutil
        self.psutil, self.root = psutil, psutil.Process(pid)
        self.stop = threading.Event()
        self.rss_peak, self.sample_count, self.cpu_peak = 0, 0, 0
        self.baselines, self.latest = {}, {}
        self.started = time.perf_counter()
        self.previous_wall, self.previous_cpu = self.started, 0
        self.process_ids = set()
        self.sample(initial=True)
        self.thread = threading.Thread(target=self.run, name='speech-resource-tree', daemon=True)
        self.thread.start()

    def sample(self, initial=False):
        memory = 0
        try:
            family = [self.root, *self.root.children(recursive=True)]
        except self.psutil.Error:
            return
        for process in family:
            try:
                memory += process.memory_info().rss
                cpu = process.cpu_times()
                elapsed = cpu.user + cpu.system
                if process.pid not in self.baselines:
                    self.baselines[process.pid] = elapsed if initial else 0
                self.latest[process.pid] = elapsed
                self.process_ids.add(process.pid)
            except self.psutil.Error:
                continue
        self.rss_peak = max(self.rss_peak, memory)
        self.sample_count += 1
        wall = time.perf_counter()
        cpu = sum(value - self.baselines[pid] for pid, value in self.latest.items())
        if wall > self.previous_wall:
            self.cpu_peak = max(self.cpu_peak, (cpu - self.previous_cpu) / (wall - self.previous_wall) * 100)
        self.previous_wall, self.previous_cpu = wall, cpu

    def run(self):
        while not self.stop.wait(.2):
            self.sample()

    def finish(self):
        self.stop.set()
        self.thread.join(2)
        self.sample()
        wall = time.perf_counter() - self.started
        cpu = sum(value - self.baselines[pid] for pid, value in self.latest.items())
        return {'measured': True, 'scope': 'launcher and recursive Python descendants; warm inference only',
                'sample_interval_s': .2, 'samples': self.sample_count, 'process_count': len(self.process_ids),
                'rss_peak_sampled_sum_bytes': self.rss_peak, 'cpu_time_sampled_s': cpu, 'wall_s': wall,
                'cpu_percent_one_core_scale_average': cpu / wall * 100, 'cpu_percent_one_core_scale_peak': self.cpu_peak}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', type=Path, action='append', required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    os.environ['PB_SPEECH_THREADS'] = str(args.threads)
    if not args.audio.resolve().is_file():
        raise ValueError('WAV fictif introuvable')
    fixtures = args.audio.resolve().parent
    with wave.open(str(args.audio), 'rb') as source:
        if source.getframerate() != 16000 or source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError('PCM16kmono nécessaire pour référence de latence')
        raw = source.readframes(source.getnframes())
    chunk = fixtures / 'benchmark-five-seconds.wav'
    with wave.open(str(chunk), 'wb') as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(raw[:160000])
    results = []
    for models in args.models:
        runtime = ResidentWhisper(fixtures, models=models.resolve())
        load_started = time.perf_counter()
        runtime.start()
        meter = ProcessTreeMeter(runtime.process.pid)
        try:
            samples = []
            for _ in range(3):
                started = time.perf_counter()
                output = runtime.transcribe(PreparedAudio(chunk, 0, 0, 5000, False), track='system')
                samples.append({'request_wall_s': time.perf_counter() - started, 'compute_s': output['compute_s'],
                                'text': ' '.join(item['text'] for item in output['segments'])})
            resources = meter.finish()
            result = {'actual_model': runtime.ready_details['model'], 'models': str(models.resolve()),
                      'model_sha256': model_fingerprint(models), 'worker_load_s': runtime.ready_details['load_s'],
                      'runtime_profile': speech_profile(models), 'runtime_profile_key': speech_profile_key(models),
                      'startup_to_ready_s': time.perf_counter() - load_started - resources['wall_s'],
                      'prewarmed_five_second_requests': samples, 'resources': resources,
                      'all_requests_under_5s': all(item['request_wall_s'] <= 5 for item in samples),
                      'direct_accuracy_qualified': False, 'sample_size': 3}
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        finally:
            meter.stop.set()
            runtime.close()
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'fixture': str(args.audio.resolve()),
              'results': results, 'simultaneous_models': False, 'production_config_changed': False,
              'real_hardware_120min_measured': False}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
