import hashlib
import sqlite3
import tempfile
import unittest
import wave
from contextlib import closing
from pathlib import Path

from verify_agent_restores import verify_files


class RestoreFileChecks(unittest.TestCase):
    def test_detects_modified_mail_and_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'brain').mkdir()
            mail = root / 'message.eml'
            raw = b'Subject: Test\r\nContent-Type: text/plain\r\n\r\nHello\r\n'
            mail.write_bytes(raw)
            audio = root / 'audio.wav'
            with wave.open(str(audio), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b'\x00\x00' * 8)
            with closing(sqlite3.connect(root / 'brain/project_brain.db')) as db, db:
                db.execute('CREATE TABLE sources(source_type,original_uri,sha256)')
                db.execute('CREATE TABLE meeting_session_chunks(storage_path,sha256,size_bytes)')
                db.execute('INSERT INTO sources VALUES(?,?,?)', ('email', str(mail), hashlib.sha256(raw).hexdigest()))
                db.execute('INSERT INTO meeting_session_chunks VALUES(?,?,?)',
                           (str(audio), hashlib.sha256(audio.read_bytes()).hexdigest(), audio.stat().st_size))
            self.assertEqual(verify_files(root)['audio'], 1)
            mail.write_bytes(raw + b'changed')
            with self.assertRaisesRegex(ValueError, 'Empreinte de mail'):
                verify_files(root)
            mail.write_bytes(raw)
            data = bytearray(audio.read_bytes())
            data[-1] ^= 1
            audio.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'Empreinte de fragment'):
                verify_files(root)


if __name__ == '__main__':
    unittest.main()
