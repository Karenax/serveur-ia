from pathlib import Path
import array
import wave
root=Path(__file__).resolve().parent.parent
with wave.open(str(root/'toolchain/voice-previews/2026-10-23/Tiphaine.wav'),'rb') as source:
    samples=array.array('h',source.readframes(source.getnframes()))
    assert source.getframerate()==24000 and source.getnchannels()==1
output=array.array('h')
for i in range(len(samples)*2//3):
    position=i*1.5
    left=int(position);fraction=position-left
    output.append(round(samples[left]*(1-fraction)+samples[min(left+1,len(samples)-1)]*fraction))
path=root/'toolchain/android-tests/conversation.wav'
with wave.open(str(path),'wb') as target:
    target.setnchannels(1);target.setsampwidth(2);target.setframerate(16000);target.writeframes(output.tobytes())
print(path)
