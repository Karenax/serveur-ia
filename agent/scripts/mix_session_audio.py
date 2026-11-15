"""Mix preserved tracks into Ogg/Opus with bounded decoding memory, no DB."""
import argparse
import heapq
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def mix(inputs, output, storage):
    import av
    import numpy as np
    from app.operational_limits import CAPTURE_DURATION_MS
    from scripts.audio_codec import BIT_RATE

    if not inputs or len(inputs) > 20000:
        raise ValueError('Nombre de fragments invalide')
    pending = []
    for index, item in enumerate(inputs):
        path = Path(item['path']).resolve()
        offset = int(item['offset_ms']) * 16
        if not path.is_relative_to(storage) or not path.is_file() or offset < 0:
            raise ValueError('Audio hors stockage autorisé')
        pending.append((offset, index, path))
    pending.sort(reverse=True)
    tracks = {item['track'] for item in inputs}
    maximum = CAPTURE_DURATION_MS * 16
    temporary = output.with_suffix(output.suffix + '.part')
    active, readers = [], []

    def frames(path):
        with av.open(str(path)) as source:
            resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
            for frame in source.decode(audio=0):
                for converted in resampler.resample(frame):
                    yield converted.to_ndarray().reshape(-1)
            for converted in resampler.resample(None):
                yield converted.to_ndarray().reshape(-1)

    cursor = 0
    try:
        with av.open(str(temporary), 'w', format='ogg') as target:
            stream = target.add_stream('libopus', rate=48000)
            stream.layout = 'mono'
            stream.bit_rate = BIT_RATE
            stream.options = {'vbr': 'off', 'application': 'voip'}
            encoder_resampler = av.AudioResampler(format='fltp', layout='mono', rate=48000)
            while pending or active:
                limit = min(cursor + 16000, maximum)
                if limit <= cursor:
                    raise ValueError('Mix audio supérieur à 12 heures')
                while pending and pending[-1][0] < limit:
                    offset, index, path = pending.pop()
                    reader = frames(path)
                    readers.append(reader)
                    first = next(reader, None)
                    if first is None:
                        raise ValueError('Fragment audio vide')
                    heapq.heappush(active, (offset, index, first, reader))
                block = np.zeros(limit - cursor, dtype=np.float32)
                used = 0
                while active and active[0][0] < limit:
                    offset, index, samples, reader = heapq.heappop(active)
                    if offset < cursor or offset + len(samples) > maximum:
                        raise ValueError('Durée ou position audio invalide')
                    amount = min(len(samples), limit - offset)
                    block[offset - cursor:offset - cursor + amount] += samples[:amount]
                    used = max(used, offset - cursor + amount)
                    if amount < len(samples):
                        heapq.heappush(active, (offset + amount, index, samples[amount:], reader))
                    else:
                        following = next(reader, None)
                        if following is not None:
                            heapq.heappush(active, (offset + amount, index, following, reader))
                length = len(block) if pending or active else used
                if length == 0:
                    break
                block = np.clip(block[:length] / max(1, len(tracks)), -1, 1)
                frame = av.AudioFrame.from_ndarray(block.reshape(1, -1), format='fltp', layout='mono')
                frame.sample_rate = 16000
                frame.pts = cursor
                for converted in encoder_resampler.resample(frame):
                    for packet in stream.encode(converted):
                        target.mux(packet)
                cursor += length
            if cursor == 0:
                raise ValueError('Mix audio vide')
            for converted in encoder_resampler.resample(None):
                for packet in stream.encode(converted):
                    target.mux(packet)
            for packet in stream.encode(None):
                target.mux(packet)
        temporary.replace(output)
    finally:
        for reader in readers:
            reader.close()
    return {'path': str(output), 'tracks': sorted(tracks), 'duration_ms': round(cursor / 16)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--storage', type=Path, required=True)
    args = parser.parse_args()
    storage = args.storage.resolve()
    request = json.loads(args.manifest.read_text(encoding='utf-8'))
    output = Path(request['output']).resolve()
    if not output.is_relative_to(storage):
        raise ValueError('Mix hors stockage autorisé')
    print(json.dumps(mix(request['inputs'], output, storage)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': f'{type(exc).__name__}: mix audio local impossible'}))
        raise SystemExit(1)
