import {afterEach, expect, it, vi} from 'vitest';
import {joinPcmWaves, needsPcmAudioRecorder, pcmWave, PcmAudioRecorder} from './pcmAudioRecorder';

afterEach(() => {vi.restoreAllMocks(); vi.unstubAllGlobals();});

const bytes = (blob: Blob) => new Promise<ArrayBuffer>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result as ArrayBuffer);
  reader.onerror = () => reject(reader.error);
  reader.readAsArrayBuffer(blob);
});

it('produit un WAV PCM mono autonome avec les valeurs et la fréquence déclarées', async () => {
  const blob = pcmWave([new Float32Array([-1, -0.5]), new Float32Array([0, 0.5, 1, NaN])], 16000);
  const view = new DataView(await bytes(blob));
  expect(blob.type).toBe('audio/wav');
  expect(String.fromCharCode(...new Uint8Array(view.buffer, 0, 4))).toBe('RIFF');
  expect(String.fromCharCode(...new Uint8Array(view.buffer, 8, 4))).toBe('WAVE');
  expect(view.getUint32(4, true)).toBe(48);
  expect(view.getUint16(22, true)).toBe(1);
  expect(view.getUint32(24, true)).toBe(16000);
  expect(view.getUint32(40, true)).toBe(12);
  expect(Array.from({length:6}, (_, i) => view.getInt16(44 + i * 2, true))).toEqual([-32768, -16384, 0, 16384, 32767, 0]);
});

it('assemble plusieurs fragments PCM en un seul WAV sans en-têtes intermédiaires', async () => {
  const first = pcmWave([new Float32Array([-1, 0.5])], 16000);
  const second = pcmWave([new Float32Array([0, 1])], 16000);
  const joined = joinPcmWaves([first, second], 16000);
  const view = new DataView(await bytes(joined));
  expect(joined.type).toBe('audio/wav');
  expect(view.byteLength).toBe(52);
  expect(view.getUint32(4, true)).toBe(44);
  expect(view.getUint32(24, true)).toBe(16000);
  expect(view.getUint32(40, true)).toBe(8);
  expect(Array.from({length:4}, (_, i) => view.getInt16(44 + i * 2, true))).toEqual([-32768, 16384, 0, 32767]);
  expect(() => joinPcmWaves([], 16000)).toThrow();
  expect(() => joinPcmWaves([new Blob(['invalid'], {type: 'audio/wav'})], 16000)).toThrow();
});

it('choisit le PCM pour WebKitGTK sans WebM, et garde MediaRecorder ailleurs', () => {
  const gtk = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/605.1.15 Version/60.5 Safari/605.1.15';
  const unsupported = {isTypeSupported: () => false};
  const webm = {isTypeSupported: (type: string) => type === 'audio/webm'};
  expect(needsPcmAudioRecorder(gtk, unsupported)).toBe(true);
  expect(needsPcmAudioRecorder(gtk, webm)).toBe(false);
  expect(needsPcmAudioRecorder('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36', unsupported)).toBe(false);
  expect(needsPcmAudioRecorder('Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Safari/605.1.15', unsupported)).toBe(false);
  expect(needsPcmAudioRecorder('Mozilla/5.0 (Linux; Android 15) AppleWebKit/605.1.15', unsupported)).toBe(false);
});

it('émet les échantillons avant pause et arrêt, sans inclure ceux reçus en pause', async () => {
  const node = () => ({connect: vi.fn(), disconnect: vi.fn()});
  const source = node(), muted = {...node(), gain: {value: 1}};
  const processor = {...node(), onaudioprocess: null as ((event: AudioProcessingEvent) => void) | null};
  const close = vi.fn(async () => undefined);
  class FakeAudioContext {
    sampleRate = 4; destination = node();
    createMediaStreamSource() {return source;}
    createScriptProcessor() {return processor;}
    createGain() {return muted;}
    resume() {return Promise.resolve();}
    close = close;
  }
  vi.stubGlobal('AudioContext', FakeAudioContext);
  const recorder = new PcmAudioRecorder({} as MediaStream);
  const blobs: Blob[] = [], events: string[] = [];
  recorder.ondataavailable = event => {blobs.push(event.data); events.push('data');};
  recorder.onstop = () => events.push('stop');
  const emit = (values: number[]) => processor.onaudioprocess?.({inputBuffer:{getChannelData:()=>new Float32Array(values)}} as unknown as AudioProcessingEvent);
  recorder.start(1000); expect(muted.gain.value).toBe(0);
  emit([0.25, 0.5]); recorder.pause();
  emit([1, 1]); recorder.resume(); emit([-0.5]); recorder.stop();
  expect(events).toEqual(['data', 'data', 'stop']);
  expect(recorder.state).toBe('inactive'); expect(close).toHaveBeenCalledTimes(1);
  const first = new DataView(await bytes(blobs[0])), second = new DataView(await bytes(blobs[1]));
  expect(first.getUint32(40, true)).toBe(4); expect(second.getUint32(40, true)).toBe(2);
  expect(second.getInt16(44, true)).toBe(-16384);
});
