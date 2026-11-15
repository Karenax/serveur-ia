"""Speech storage: independent Ogg/Opus files at 32 kbit/s, mono.

Only encoding requires PyAV (the existing speech runtime). Container validation
and crash recovery use the standard library and never open an audio device.
"""
import io
import struct

BIT_RATE = 32000


def encode_opus(raw):
    import av
    import numpy as np

    output = io.BytesIO()
    with av.open(output, 'w', format='ogg') as container:
        stream = container.add_stream('libopus', rate=48000)
        stream.layout = 'mono'
        stream.bit_rate = BIT_RATE
        stream.options = {'vbr': 'off', 'application': 'voip'}
        resampler = av.AudioResampler(format='s16', layout='mono', rate=48000)
        frame = av.AudioFrame.from_ndarray(np.frombuffer(raw, dtype='<i2').reshape(1, -1),
                                           format='s16', layout='mono')
        frame.sample_rate = 16000
        frame.pts = 0
        for converted in [*resampler.resample(frame), *resampler.resample(None)]:
            for packet in stream.encode(converted):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    # libavformat chooses a random Ogg serial. Freeze it so a producer retry
    # of the same PCM has the same bytes, SHA and durable command identity.
    data = bytearray(output.getvalue())
    position = 0
    while position < len(data):
        count = data[position + 26]
        end = position + 27 + count + sum(data[position + 27:position + 27 + count])
        data[position + 14:position + 18] = bytes(4)
        data[position + 22:position + 26] = bytes(4)
        struct.pack_into('<I', data, position + 22, _crc(data[position:end]))
        position = end
    return bytes(data)


def _crc(data):
    value = 0
    for byte in data:
        value ^= byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04c11db7 if value & 0x80000000 else 0)) & 0xffffffff
    return value


def opus_duration_ms(data):
    """Validate one complete Ogg/Opus stream, including page CRC and timeline."""
    position = sequence = 0
    serial = preskip = None
    final = None
    while position < len(data):
        header = data[position:position + 27]
        if len(header) != 27 or header[:5] != b'OggS\x00':
            raise ValueError('Invalid Ogg page')
        count = header[26]
        lacing = data[position + 27:position + 27 + count]
        end = position + 27 + count + sum(lacing)
        if len(lacing) != count or end > len(data) or final is not None:
            raise ValueError('Truncated or chained Ogg stream')
        page = bytearray(data[position:end])
        checksum = struct.unpack_from('<I', page, 22)[0]
        page[22:26] = bytes(4)
        if _crc(page) != checksum:
            raise ValueError('Ogg checksum differs')
        current_serial, current_seq = struct.unpack_from('<II', header, 14)
        if current_seq != sequence or (serial is not None and serial != current_serial):
            raise ValueError('Ogg sequence differs')
        if sequence == 0:
            body = data[position + 27 + count:end]
            if not header[5] & 2 or len(body) != 19 or body[:10] != b'OpusHead\x01\x01' or body[18] != 0:
                raise ValueError('Mono Opus header required')
            preskip = struct.unpack_from('<H', body, 10)[0]
            serial = current_serial
        if header[5] & 4:
            final = struct.unpack_from('<Q', header, 6)[0]
        sequence += 1
        position = end
    if final is None or preskip is None or final <= preskip:
        raise ValueError('Complete nonempty Opus stream required')
    return round((final - preskip) / 48)
