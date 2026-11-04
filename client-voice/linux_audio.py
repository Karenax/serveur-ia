"""Session-scoped PulseAudio/PipeWire capture. Audio stays in memory."""
import os
import select
import shutil
import subprocess
import time


class PulseMicrophone:
    """Bounded reads of 16 kHz mono PCM from parec; close releases capture."""
    def __init__(self, resources=None):
        if not shutil.which('parec'):
            raise OSError('Le microphone nécessite pulseaudio-utils. Installez ce paquet puis relancez Kiara.')
        command = ['parec','--raw','--format=s16le','--rate=16000','--channels=1',
                   '--latency-msec=100','--client-name=Kiara','--stream-name=Microphone Kiara']
        self.process = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL,bufsize=0)
        self.pending = b''
        self.aec = False
        os.set_blocking(self.process.stdout.fileno(),False)

    def read(self):
        if self.process is None:
            raise OSError('Le microphone est fermé.')
        descriptor = self.process.stdout.fileno()
        if not select.select([descriptor],[],[],.1)[0]:
            if self.process.poll() is not None:
                raise OSError('Le microphone est inaccessible. Vérifiez l’entrée audio dans les réglages Linux puis réessayez.')
            return b''
        try:
            value = os.read(descriptor,3200)
        except BlockingIOError:
            return b''
        if not value:
            raise OSError('Le microphone a été déconnecté. Vérifiez les réglages audio Linux puis réessayez.')
        data = self.pending+value
        length = len(data)//2*2
        self.pending = data[length:]
        return data[:length]

    def close(self):
        process,self.process = self.process,None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=2)
        finally:
            process.stdout.close()
            self.pending = b''


def audio_self_test():
    """Exercise capture without models, a server, or recording files."""
    microphone = PulseMicrophone()
    count = 0
    deadline = time.monotonic()+5
    try:
        while count < 16000 and time.monotonic() < deadline:
            count += len(microphone.read())//2
        if count < 16000:
            raise OSError('Aucun son reçu du microphone. Vérifiez les réglages audio Linux.')
        return {'passed':True,'rate':16000,'captured_samples':count,'aec':microphone.aec}
    finally:
        microphone.close()
