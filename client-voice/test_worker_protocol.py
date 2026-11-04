"""Cancellation and parent closure apply equally to all voice worker generations."""
import io
import json
import unittest
from unittest.mock import patch
from worker_protocol import CommandInbox


class WorkerProtocolTests(unittest.TestCase):
    def test_worker_reads_utf8_french_even_when_windows_stdin_defaults_to_cp1252(self):
        text='Léa lança les dés. Son pion avança d’une case.'
        data=(json.dumps({'action':'speak','id':'a'*32,'text':text},ensure_ascii=False)+'\n').encode('utf-8')
        with io.TextIOWrapper(io.BytesIO(data),encoding='cp1252') as stream:
            with patch('worker_protocol.sys.stdin',stream):
                inbox=CommandInbox('tts');inbox.read()
            self.assertEqual(inbox.commands.get_nowait()['text'],text)
            self.assertEqual(stream.encoding,'utf-8')

    def test_cancel_before_start_and_different_request_remain_independent(self):
        inbox=CommandInbox('asr');first='a'*32;second='b'*32
        inbox.accept({'action':'cancel','id':first})
        inbox.begin(first);self.assertTrue(inbox.stop.is_set());inbox.finish()
        inbox.begin(second);self.assertFalse(inbox.stop.is_set())
        inbox.accept({'action':'cancel','id':second});self.assertTrue(inbox.stop.is_set())

    def test_parent_eof_or_malformed_input_prevents_further_inference(self):
        for text in ('', '{not json}\n'):
            inbox=CommandInbox('tts',io.StringIO(text));inbox.read();inbox.begin('a'*32)
            self.assertTrue(inbox.closed.is_set());self.assertTrue(inbox.stop.is_set())

    def test_cancel_bookkeeping_is_bounded_and_wrong_actions_are_refused(self):
        inbox=CommandInbox('asr')
        for number in range(200):inbox.accept({'action':'cancel','id':f'{number:032x}'})
        self.assertEqual(len(inbox.cancelled),64)
        with self.assertRaises(ValueError):inbox.accept({'action':'speak','id':'a'*32})


if __name__=='__main__':unittest.main()
