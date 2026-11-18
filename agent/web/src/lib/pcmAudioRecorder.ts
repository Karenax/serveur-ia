/**
 * WebKitGTK can accept a microphone while MediaRecorder's MP4 path emits only
 * empty blobs. Record independent PCM WAV fragments through Web Audio instead.
 * The caller remains responsible for persisting and acknowledging each blob.
 */
export function isLinuxWebKit(userAgent: string): boolean {
  return /Linux/i.test(userAgent) && /AppleWebKit/i.test(userAgent) && !/Android|Chrome|Chromium|CriOS|Edg\//i.test(userAgent);
}

export function needsPcmAudioRecorder(userAgent: string, recorder: Pick<typeof MediaRecorder, 'isTypeSupported'>): boolean {
  return isLinuxWebKit(userAgent) && !['audio/webm;codecs=opus', 'audio/webm'].some(type => recorder.isTypeSupported?.(type));
}

function pcmWaveHeader(dataBytes: number, rate: number): ArrayBuffer {
  if (!Number.isSafeInteger(dataBytes) || dataBytes < 0 || dataBytes > 0xffffffff - 36 || dataBytes % 2 ||
      !Number.isInteger(rate) || rate < 1 || rate > 0xffffffff / 2) throw new Error('Format audio invalide.');
  const buffer = new ArrayBuffer(44);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i));
  };
  text(0, 'RIFF'); view.setUint32(4, 36 + dataBytes, true); text(8, 'WAVE');
  text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, 'data'); view.setUint32(40, dataBytes, true);
  return buffer;
}

export function joinPcmWaves(chunks: readonly Blob[], rate: number): Blob {
  if (!chunks.length || chunks.some(chunk => chunk.type !== 'audio/wav' || chunk.size < 44 || (chunk.size - 44) % 2)) {
    throw new Error('Fragments audio invalides.');
  }
  const dataBytes = chunks.reduce((total, chunk) => total + chunk.size - 44, 0);
  if (!dataBytes) throw new Error('Aucun son enregistré.');
  return new Blob([pcmWaveHeader(dataBytes, rate), ...chunks.map(chunk => chunk.slice(44))], {type: 'audio/wav'});
}

export function pcmWave(samples: readonly Float32Array[], rate: number): Blob {
  const count = samples.reduce((total, block) => total + block.length, 0);
  const buffer = new ArrayBuffer(44 + count * 2);
  new Uint8Array(buffer).set(new Uint8Array(pcmWaveHeader(count * 2, rate)));
  const view = new DataView(buffer);
  let offset = 44;
  for (const block of samples) for (const value of block) {
    const sample = Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0;
    view.setInt16(offset, sample < 0 ? Math.round(sample * 32768) : Math.round(sample * 32767), true);
    offset += 2;
  }
  return new Blob([buffer], {type: 'audio/wav'});
}

export class PcmAudioRecorder {
  readonly mimeType = 'audio/wav';
  state: RecordingState = 'inactive';
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  private context?: AudioContext;
  private source?: MediaStreamAudioSourceNode;
  private processor?: ScriptProcessorNode;
  private muted?: GainNode;
  private samples: Float32Array[] = [];
  private count = 0;
  private target = 0;

  constructor(private readonly stream: MediaStream) {}

  get sampleRate() {return this.context?.sampleRate;}

  private flush() {
    if (!this.count || !this.context) return;
    const blob = pcmWave(this.samples, this.context.sampleRate);
    this.samples = []; this.count = 0;
    this.ondataavailable?.({data: blob} as BlobEvent);
  }

  start(timeslice = 2000) {
    if (this.state !== 'inactive') throw new Error('La capture audio est déjà démarrée.');
    let context: AudioContext;
    try {context = new AudioContext({sampleRate: 16000});} catch {context = new AudioContext();}
    this.context = context;
    try {
      this.source = context.createMediaStreamSource(this.stream);
      this.processor = context.createScriptProcessor(2048, 1, 1);
      this.muted = context.createGain(); this.muted.gain.value = 0;
      this.target = Math.max(1, Math.round(context.sampleRate * timeslice / 1000));
      this.processor.onaudioprocess = event => {
        if (this.state !== 'recording') return;
        const block = event.inputBuffer.getChannelData(0).slice();
        this.samples.push(block); this.count += block.length;
        if (this.count >= this.target) this.flush();
      };
      this.source.connect(this.processor); this.processor.connect(this.muted); this.muted.connect(context.destination);
      this.state = 'recording';
      void context.resume().catch(() => {if (this.state !== 'inactive') this.onerror?.(new Event('error'));});
    } catch (error) {
      this.source?.disconnect(); this.processor?.disconnect(); this.muted?.disconnect();
      void context.close().catch(() => undefined);
      this.context = undefined;
      throw error;
    }
  }

  pause() {if (this.state === 'recording') {this.state = 'paused'; this.flush();}}
  resume() {if (this.state === 'paused') this.state = 'recording';}
  stop() {
    if (this.state === 'inactive') return;
    this.state = 'inactive';
    if (this.processor) this.processor.onaudioprocess = null;
    this.flush();
    this.source?.disconnect(); this.processor?.disconnect(); this.muted?.disconnect();
    if (this.context) void this.context.close().catch(() => undefined);
    this.onstop?.(new Event('stop'));
  }
}
