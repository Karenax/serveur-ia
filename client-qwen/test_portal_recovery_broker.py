"""Fictional records only; exercise the real loopback broker."""
import hashlib
import http.client
import json
import socket
import threading
import unittest

from portal_recovery_broker import PortalRecoveryBroker, RecoveryUnavailable
from portal_origin_plan import OriginInventoryPlan

ASSETS = {'/recovery': b'<!doctype html>', '/recovery.js': b'void 0;',
          '/portal_origin_recovery.js': b'void 0;'}


def available_ports(count=2):
    sockets = []
    try:
        for _ in range(count):
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def request(port, method, path, body=b'', headers=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        result = connection.getresponse()
        return result.status, dict(result.getheaders()), result.read()
    finally:
        connection.close()


class RecoveryBrokerTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = available_ports()
        self.broker = PortalRecoveryBroker([self.a, self.b], self.a, ASSETS, max_bytes=64).start()
        self.addCleanup(self.broker.close)

    def headers(self, port, token=None, origin=None):
        return {'Origin': origin or f'http://127.0.0.1:{port}',
                'X-Kiara-Recovery': self.broker.token if token is None else token}

    def post(self, port, path, body=b'', **kwargs):
        return request(port, 'POST', path, body, self.headers(port, **kwargs))

    def test_transfer_is_replayable_until_verified_ack_and_never_overwrites(self):
        body = b'fragment audio fictif'
        digest = hashlib.sha256(body).hexdigest()
        status, _, response = self.post(self.b, '/recovery/stage', body)
        prepared = json.loads(response)
        self.assertEqual(status, 200)
        self.assertEqual(prepared['sha256'], digest)
        self.assertEqual(len(prepared['id']), 32)
        status, _, repeated = self.post(self.b, '/recovery/stage', body)
        self.assertEqual((status, json.loads(repeated)), (200, prepared))
        self.assertEqual(self.post(self.b, '/recovery/stage', b'autre')[0], 409)
        for _ in range(2):
            status, headers, record = self.post(self.a, '/recovery/read')
            self.assertEqual((status, record), (200, body))
            self.assertEqual(headers['X-Kiara-Transfer-ID'], prepared['id'])
            self.assertEqual(headers['X-Kiara-Record-SHA256'], digest)
            self.assertEqual(headers['X-Kiara-Source-Port'], str(self.b))
        self.assertEqual(self.post(self.a, '/recovery/ack', b'wrong')[0], 409)
        self.assertEqual(self.post(self.a, '/recovery/read')[2], body)
        self.assertEqual(self.post(self.b, '/recovery/receipt', prepared['id'].encode())[0], 404)
        receipt = f"{prepared['id']}:{digest}".encode()
        self.assertEqual(self.post(self.a, '/recovery/ack', receipt)[0], 200)
        self.assertEqual(self.post(self.a, '/recovery/read')[0], 404)
        self.assertEqual(self.post(self.a, '/recovery/receipt', prepared['id'].encode())[0], 403)
        self.assertEqual(json.loads(self.post(self.b, '/recovery/receipt', prepared['id'].encode())[2]), prepared)
        status, _, response = self.post(self.b, '/recovery/stage', body)
        next_transfer = json.loads(response)
        self.assertEqual(status, 200)
        self.assertNotEqual(next_transfer['id'], prepared['id'])
        self.assertEqual(self.post(self.b, '/recovery/receipt', prepared['id'].encode())[0], 404)
        self.assertEqual(self.post(self.a, '/recovery/ack', receipt)[0], 409)
        self.assertEqual(self.post(self.a, '/recovery/read')[2], body)

    def test_other_origins_and_wrong_tokens_cannot_read_or_stage(self):
        self.assertEqual(self.post(self.b, '/recovery/stage', b'draft')[0], 200)
        self.assertEqual(self.post(self.a, '/recovery/read', token='bad')[0], 403)
        self.assertEqual(self.post(self.a, '/recovery/read', origin='https://example.test')[0], 403)
        self.assertEqual(self.post(self.b, '/recovery/read')[0], 403)
        self.assertEqual(self.post(self.b, '/recovery/ack', b'wrong')[0], 403)
        self.assertEqual(self.post(self.a, '/recovery/stage', b'draft')[0], 400)
        status, _, value = request(self.a, 'POST', '/recovery/read', b'', {'Host':'attacker.test', **self.headers(self.a)})
        self.assertEqual((status, value), (403, b''))
        self.assertEqual(self.post(self.a, '/recovery/read')[2], b'draft')

    def test_bounded_input_and_invalid_paths_are_rejected(self):
        # The broker rejects the declared size before reading the body. Sending
        # unread bytes here can reset the connection instead of returning 413 on Windows.
        oversized = {**self.headers(self.b), 'Content-Length': '65'}
        self.assertEqual(request(self.b, 'POST', '/recovery/stage', headers=oversized)[0], 413)
        self.assertEqual(self.post(self.b, '/recovery/stage', b'')[0], 400)
        self.assertEqual(self.post(self.b, '/other')[0], 404)
        self.assertEqual(self.post(self.a, '/recovery/read')[0], 404)
        self.assertEqual(self.post(self.b, '/recovery/receipt', b'not-an-identifier')[0], 400)

    def test_static_assets_are_scoped_and_never_cached(self):
        status, headers, data = request(self.a, 'GET', '/recovery')
        self.assertEqual((status, data), (200, ASSETS['/recovery']))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(request(self.a, 'GET', '/recovery?token=anything')[0], 404)
        self.assertEqual(request(self.a, 'GET', '/other')[0], 404)


class RecoveryReservationTests(unittest.TestCase):
    def test_destination_manifest_is_private_bounded_and_not_a_transfer(self):
        source,destination,other=available_ports(3)
        with self.assertRaises(ValueError):
            PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                 result_source=source,result_mode='manifest',allow_same_origin_transfer=True)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,
                                  result_source=destination,result_mode='manifest',allow_same_origin_transfer=True) as broker:
            def send(port,path,value=b''):
                return request(port,'POST',path,value,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            ids=['b'*64,'a'*64];value={'status':'manifest','audioArchiveIds':ids}
            body=json.dumps(value).encode()
            self.assertEqual(send(other,'/recovery/result',body)[0],403)
            self.assertEqual(send(destination,'/recovery/stage',b'private')[0],409)
            for invalid in ({**value,'audioArchiveIds':['a'*64,'a'*64]}, {**value,'audioArchiveIds':['bad']},
                            {**value,'extra':'private'}):
                self.assertEqual(send(destination,'/recovery/result',json.dumps(invalid).encode())[0],400)
            self.assertEqual(send(destination,'/recovery/result',body)[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'manifest','audioArchiveIds':sorted(ids)})

    def test_extended_inventory_accepts_only_a_valid_bounded_archive_manifest(self):
        first,second=available_ports();ports=(first,second)
        plan=OriginInventoryPlan(ports,default_port=first,allow_audio_archives=True,require_audio_ids=True)
        assets={**ASSETS,'/portal_audio_conflict_archive.js':b'void 0;'}
        with PortalRecoveryBroker(ports,first,assets,inventory_plan=plan) as broker:
            def send(port,value):
                return request(port,'POST','/recovery/inventory',json.dumps(value).encode(),
                    {'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            ids=[format(n,'064x') for n in range(50)]
            report={'localEntries':0,'audioChunks':0,'audioArchives':len(ids),'audioArchiveIds':ids}
            self.assertGreater(len(json.dumps(report)),1024)
            self.assertEqual(send(first,{**report,'audioArchives':49})[0],400)
            self.assertEqual(send(first,report)[0],200)
            self.assertEqual(send(second,{'localEntries':0,'audioChunks':0,'audioArchives':0,'audioArchiveIds':[]})[0],200)
            self.assertEqual(plan.status()['port'],first)
            self.assertEqual(plan.reports()[0]['audioArchiveIds'],ids)

    def test_audio_resources_require_the_experimental_audio_option(self):
        source,destination=available_ports();assets={**ASSETS,'/portal_audio_conflict_archive.js':b'void 0;'}
        with self.assertRaises(ValueError):
            PortalRecoveryBroker([source,destination],destination,assets,require_receipt=True,
                                 result_source=source,allow_review=True)
        with PortalRecoveryBroker([source,destination],destination,assets,require_receipt=True,
                                  result_source=source,allow_review=True,allow_audio_review=True):
            self.assertEqual(request(destination,'GET','/portal_audio_conflict_archive.js')[0],200)

    def test_audio_review_requires_explicit_option_and_typed_proof_for_current_record(self):
        source,destination=available_ports();record=b'{"type":"audio","meta":{},"mime":"audio/wav","data":"AA=="}'
        for enabled in (False,True):
            with self.subTest(enabled=enabled),PortalRecoveryBroker(
                    [source,destination],destination,ASSETS,require_receipt=True,result_source=source,
                    allow_review=True,allow_audio_review=enabled) as broker:
                def send(port,path,body=b''):
                    return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
                transfer=json.loads(send(source,'/recovery/stage',record)[2])
                receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
                self.assertEqual(send(destination,'/recovery/review',receipt)[0],200 if enabled else 409)
                self.assertEqual(broker.take_review_request(),enabled)
                self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'c'*64)[0],409)
                self.assertEqual(send(destination,'/recovery/archive',receipt+b':audio-'+b'c'*64)[0],200 if enabled else 409)
                if enabled:
                    self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],200)
                    self.assertEqual(send(source,'/recovery/receipt',transfer['id'].encode())[0],200)
                    self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0,"archived":1}')[0],200)
                    self.assertEqual(broker.verified_archive_ids(),('audio-'+'c'*64,))

    def test_audio_segments_and_local_records_cannot_claim_an_audio_archive(self):
        source,destination=available_ports()
        for body in (b'{"type":"audio-part","id":"x","offset":0,"data":"AA=="}',
                     b'{"type":"local","key":"draft","value":"fiction"}',
                     b'{"type":"audio-end","id":"x","id":"y"}'):
            with self.subTest(body=body),PortalRecoveryBroker(
                    [source,destination],destination,ASSETS,require_receipt=True,result_source=source,
                    allow_review=True,allow_audio_review=True) as broker:
                def send(port,path,payload=b''):
                    return request(port,'POST',path,payload,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
                transfer=json.loads(send(source,'/recovery/stage',body)[2])
                receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
                self.assertEqual(send(destination,'/recovery/archive',receipt+b':audio-'+b'a'*64)[0],409)

    def test_audio_media_is_limited_to_interactive_destination_transfer_page(self):
        source,destination=available_ports(2)
        assets={**ASSETS,'/recovery/transfer':b'<!doctype html>','/recovery/scan':b'<!doctype html>'}
        with PortalRecoveryBroker([source,destination],destination,assets,require_receipt=True,
                                  result_source=source,allow_review=True):
            csp=lambda port,path:request(port,'GET',path)[1]['Content-Security-Policy']
            self.assertIn('media-src blob:',csp(destination,'/recovery/transfer'))
            self.assertNotIn('media-src',csp(source,'/recovery/transfer'))
            self.assertNotIn('media-src',csp(destination,'/recovery/scan'))
            self.assertNotIn('media-src',csp(destination,'/recovery'))
        with PortalRecoveryBroker([source,destination],destination,assets,require_receipt=True,
                                  result_source=source):
            self.assertNotIn('media-src',request(destination,'GET','/recovery/transfer')[1]['Content-Security-Policy'])

    def test_review_request_is_private_and_bound_to_the_pending_local_record(self):
        source,destination,other=available_ports(3)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True) as broker:
            def send(port,path,body=b'',token=None):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}',
                    'X-Kiara-Recovery':broker.token if token is None else token})
            self.assertEqual(send(source,'/recovery/options')[0],403)
            self.assertEqual(send(destination,'/recovery/options',token='bad')[0],403)
            self.assertEqual(json.loads(send(destination,'/recovery/options')[2]),{'review':True,'preserve':False,'required':[]})
            self.assertEqual(send(destination,'/recovery/review',b'x')[0],409)
            record=b'{"type":"local","key":"draft","value":"fiction"}'
            transfer=json.loads(send(source,'/recovery/stage',record)[2])
            identifier=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(send(source,'/recovery/review',identifier)[0],403)
            self.assertEqual(send(other,'/recovery/review',identifier)[0],403)
            self.assertEqual(send(destination,'/recovery/review',identifier,token='bad')[0],403)
            altered=identifier[:-1]+(b'1' if identifier[-1:]==b'0' else b'0')
            self.assertEqual(send(destination,'/recovery/review',altered)[0],409)
            self.assertFalse(broker.take_review_request())
            self.assertEqual(send(destination,'/recovery/review',identifier)[0],200)
            self.assertTrue(broker.take_review_request())
            self.assertFalse(broker.take_review_request())
            self.assertEqual(send(destination,'/recovery/ack',identifier+b':conflict')[0],200)
            self.assertEqual(send(destination,'/recovery/review',identifier)[0],409)
            self.assertEqual(send(source,'/recovery/receipt',transfer['id'].encode())[0],200)
            audio=json.loads(send(source,'/recovery/stage',b'{"type":"audio","key":"x","value":"y"}')[2])
            audio_id=f"{audio['id']}:{audio['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/review',audio_id)[0],409)
            self.assertFalse(broker.take_review_request())

    def test_review_is_disabled_without_explicit_transfer_option(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,result_source=source) as broker:
            headers={'Origin':f'http://127.0.0.1:{destination}','X-Kiara-Recovery':broker.token}
            self.assertEqual(request(destination,'POST','/recovery/review',b'',headers)[0],404)
            self.assertFalse(broker.take_review_request())

    def test_archived_receipt_is_limited_to_local_records_and_counted_exactly(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"draft","value":"old"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':restart')[0],409)
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],409)
            self.assertEqual(send(source,'/recovery/archive',receipt+b':'+b'c'*64)[0],403)
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'c'*64)[0],200)
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],200)
            self.assertEqual(json.loads(send(source,'/recovery/receipt',transfer['id'].encode())[2])['status'],'archived')
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":1}')[0],409)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0,"archived":1}')[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'ok','copied':0,'identical':0,'archived':1})
            self.assertEqual(broker.verified_archive_ids(),('c'*64,))

    def test_required_archives_must_be_verified_before_any_transfer_is_read(self):
        source,destination=available_ports();required=('a'*64,'b'*64)
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True,required_archives=required) as broker:
            def send(port,path,body=b'',token=None):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}',
                    'X-Kiara-Recovery':broker.token if token is None else token})
            body=b'{"type":"local","key":"draft","value":"fiction"}'
            transfer=json.loads(send(source,'/recovery/stage',body)[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(json.loads(send(destination,'/recovery/options')[2])['required'],list(required))
            self.assertEqual(send(destination,'/recovery/read')[0],409)
            self.assertEqual(send(destination,'/recovery/review',receipt)[0],409)
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'c'*64)[0],409)
            self.assertEqual(send(source,'/recovery/required-ok')[0],403)
            self.assertEqual(send(destination,'/recovery/required-ok',token='bad')[0],403)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0}')[0],409)
            self.assertEqual(send(destination,'/recovery/required-ok')[0],200)
            self.assertEqual(send(destination,'/recovery/read')[2],body)
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'c'*64)[0],200)
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],200)
            self.assertEqual(send(source,'/recovery/receipt',transfer['id'].encode())[0],200)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0,"archived":1}')[0],200)
            self.assertEqual(broker.verified_archive_ids(),('c'*64,))

    def test_invalid_required_archive_lists_are_refused(self):
        source,destination=available_ports()
        for required in (('a'*64,'a'*64),('A'*64,),('short',)):
            with self.subTest(required=required),self.assertRaises(ValueError):
                PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                     result_source=source,allow_review=True,required_archives=required)
        with self.assertRaises(ValueError):
            PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                 result_source=source,required_archives=('a'*64,))
        with self.assertRaises(ValueError):
            PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                 result_source=source,allow_review=True,required_archives=('audio-'+'a'*64,))
        with self.assertRaises(ValueError):
            PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                 result_source=source,allow_audio_review=True)

    def test_audio_archives_block_transfer_until_destination_verifies_them(self):
        source,destination=available_ports();required=('audio-'+'a'*64,)
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,result_source=source,
                                  allow_review=True,allow_audio_review=True,required_archives=required) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"audio-end","id":"fiction"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/read')[0],409)
            self.assertEqual(send(destination,'/recovery/review',receipt)[0],409)
            self.assertEqual(send(destination,'/recovery/required-ok')[0],200)
            self.assertEqual(send(destination,'/recovery/review',receipt)[0],200)
            self.assertTrue(broker.take_review_request())
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':restart')[0],200)
            self.assertEqual(json.loads(send(source,'/recovery/receipt',transfer['id'].encode())[2])['status'],'restart')
            self.assertEqual(send(source,'/recovery/result',b'{"status":"restart"}')[0],200)

    def test_missing_required_archive_is_reported_only_by_the_destination(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True,required_archives=('a'*64,)) as broker:
            def send(port,path,token=None):
                return request(port,'POST',path,b'',{'Origin':f'http://127.0.0.1:{port}',
                    'X-Kiara-Recovery':broker.token if token is None else token})
            self.assertEqual(send(source,'/recovery/archive-unavailable')[0],403)
            self.assertEqual(send(destination,'/recovery/archive-unavailable','bad')[0],403)
            self.assertEqual(send(destination,'/recovery/archive-unavailable')[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'archive-unavailable'})
            self.assertEqual(send(destination,'/recovery/required-ok')[0],409)

    def test_archive_proof_is_bound_to_one_pending_record_and_cannot_be_reused(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            first=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"a","value":"one"}')[2])
            receipt=f"{first['id']}:{first['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'c'*64)[0],200)
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'd'*64)[0],409)
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],200)
            self.assertEqual(send(source,'/recovery/receipt',first['id'].encode())[0],200)
            second=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"b","value":"two"}')[2])
            second_receipt=f"{second['id']}:{second['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/archive',receipt+b':'+b'd'*64)[0],409)
            self.assertEqual(send(destination,'/recovery/archive',second_receipt+b':'+b'c'*64)[0],409)
            self.assertEqual(send(destination,'/recovery/ack',second_receipt+b':archived')[0],409)
            self.assertEqual(send(destination,'/recovery/archive',second_receipt+b':'+b'd'*64)[0],200)
            self.assertEqual(send(destination,'/recovery/ack',second_receipt+b':archived')[0],200)
            self.assertEqual(broker.verified_archive_ids(),('c'*64,'d'*64))

    def test_restart_requires_review_of_the_same_pending_record(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            self.assertEqual(send(source,'/recovery/result',b'{"status":"restart"}')[0],409)
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"draft","value":"old"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':restart')[0],409)
            self.assertEqual(send(destination,'/recovery/review',receipt)[0],200)
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':restart')[0],200)
            self.assertEqual(json.loads(send(source,'/recovery/receipt',transfer['id'].encode())[2])['status'],'restart')
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":1}')[0],409)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"restart"}')[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'restart'})

    def test_archived_or_restart_cannot_ack_an_audio_record_or_an_unenabled_broker(self):
        for enabled in (False,True):
            source,destination=available_ports()
            with self.subTest(enabled=enabled),PortalRecoveryBroker([source,destination],destination,ASSETS,
                    require_receipt=True,result_source=source,allow_review=enabled) as broker:
                def send(port,path,body=b''):
                    return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
                body=b'{"type":"audio","key":"a","value":"b"}' if enabled else b'{"type":"local","key":"a","value":"b"}'
                transfer=json.loads(send(source,'/recovery/stage',body)[2]);receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
                self.assertEqual(send(destination,'/recovery/ack',receipt+b':archived')[0],409)
                self.assertEqual(send(destination,'/recovery/ack',receipt+b':restart')[0],409)
                self.assertEqual(send(destination,'/recovery/read')[2],body)

    def test_receiver_start_requires_authenticated_destination(self):
        source,destination,other=available_ports(3)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,
                                  result_source=source) as broker:
            def send(port,token):
                return request(port,'POST','/recovery/options',b'',{'Origin':f'http://127.0.0.1:{port}',
                    'X-Kiara-Recovery':token})[0]
            self.assertFalse(broker.receiver_started())
            self.assertEqual(send(source,broker.token),403)
            self.assertEqual(send(other,broker.token),403)
            self.assertEqual(send(destination,'wrong'),403)
            self.assertFalse(broker.receiver_started())
            self.assertEqual(send(destination,broker.token),200)
            self.assertTrue(broker.receiver_started())

    def test_receiver_failure_immediately_reports_unavailable_without_dropping_pending_data(self):
        source,destination,other=available_ports(3)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True) as broker:
            def send(port,path,body=b'',token=None):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}',
                    'X-Kiara-Recovery':broker.token if token is None else token})
            body=b'{"type":"local","key":"draft","value":"fiction"}'
            self.assertEqual(send(source,'/recovery/stage',body)[0],200)
            self.assertEqual(send(source,'/recovery/fail')[0],403)
            self.assertEqual(send(other,'/recovery/fail')[0],403)
            self.assertEqual(send(destination,'/recovery/fail',token='bad')[0],403)
            self.assertEqual(send(destination,'/recovery/fail')[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'unavailable'})
            self.assertEqual(send(destination,'/recovery/read')[2],body)
            self.assertEqual(send(destination,'/recovery/fail')[0],409)

    def test_review_error_is_never_converted_to_automatic_preservation(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,allow_review=True,preserve_conflicts=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"draft","value":"old"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}:unavailable".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            self.assertEqual(json.loads(send(source,'/recovery/receipt',transfer['id'].encode())[2])['status'],'unavailable')
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0,"preserved":1}')[0],409)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"unavailable"}')[0],200)

    def test_snapshot_channel_accepts_only_bounded_digest_from_source(self):
        source,destination,other=available_ports(3)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,
                                  result_source=source,result_mode='snapshot') as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            value={'status':'snapshot','localEntries':1,'audioChunks':2,'digest':'a'*64}
            body=json.dumps(value).encode()
            self.assertEqual(send(other,'/recovery/result',body)[0],403)
            self.assertEqual(send(source,'/recovery/stage',b'private')[0],409)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0}')[0],400)
            self.assertEqual(send(source,'/recovery/result',json.dumps({**value,'digest':'A'*64}).encode())[0],400)
            self.assertEqual(send(source,'/recovery/result',json.dumps({**value,'extra':'private'}).encode())[0],400)
            self.assertEqual(send(source,'/recovery/result',body)[0],200)
            self.assertEqual(broker.wait_result(0),value)

    def test_extended_snapshot_requires_opt_in_and_valid_archive_counts(self):
        source,destination=available_ports();value={'status':'snapshot','localEntries':1,'audioChunks':0,
                                                   'audioArchives':2,'digest':'a'*64}
        for enabled in (False,True):
            with self.subTest(enabled=enabled),PortalRecoveryBroker([source,destination],destination,ASSETS,
                    require_receipt=True,result_source=source,result_mode='snapshot',snapshot_audio_archives=enabled) as broker:
                def send(body):
                    return request(source,'POST','/recovery/result',body,{'Origin':f'http://127.0.0.1:{source}',
                                                                         'X-Kiara-Recovery':broker.token})
                for bad in ({**value,'audioArchives':True},{**value,'audioArchives':3001}):
                    self.assertEqual(send(json.dumps(bad).encode())[0],400)
                self.assertEqual(send(json.dumps(value).encode())[0],200 if enabled else 400)
                if enabled:self.assertEqual(broker.wait_result(0),value)
    def test_result_is_bounded_private_and_requires_all_receipts(self):
        source,destination,other=available_ports(3)
        with PortalRecoveryBroker([source,destination,other],destination,ASSETS,require_receipt=True,result_source=source) as broker:
            def send(port,path,body=b'',token=None):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token if token is None else token})
            result=b'{"status":"ok","copied":1,"identical":0}'
            self.assertEqual(send(source,'/recovery/result',result)[0],409)
            self.assertEqual(send(other,'/recovery/stage',b'draft')[0],403)
            self.assertEqual(send(other,'/recovery/result',result)[0],403)
            self.assertEqual(send(source,'/recovery/result',result,token='wrong')[0],403)
            for malformed in (b'{"status":"ok","copied":true,"identical":0}',
                              b'{"status":"ok","status":"conflict"}',
                              b'{"status":"ok","copied":-1,"identical":0}',b'{"status":"conflict","private":"draft"}'):
                self.assertEqual(send(source,'/recovery/result',malformed)[0],400)
            status,_,body=send(source,'/recovery/stage',b'draft');self.assertEqual(status,200)
            transfer=json.loads(body);receipt=f"{transfer['id']}:{transfer['sha256']}:copied".encode()
            self.assertEqual(send(source,'/recovery/result',result)[0],409)
            self.assertEqual(send(destination,'/recovery/ack',receipt.rsplit(b':',1)[0])[0],409)
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            self.assertEqual(send(source,'/recovery/result',result)[0],409)
            self.assertEqual(send(source,'/recovery/receipt',transfer['id'].encode())[0],200)
            self.assertIsNone(broker.wait_result(0))
            self.assertEqual(send(source,'/recovery/result',result)[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'ok','copied':1,'identical':0})
            self.assertEqual(send(source,'/recovery/result',result)[0],200)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"unavailable"}')[0],409)
            self.assertEqual(send(source,'/recovery/stage',b'other')[0],409)

    def test_conflict_cannot_be_reported_as_success(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,result_source=source) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'draft')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}:conflict".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            self.assertEqual(send(source,'/recovery/receipt',transfer['id'].encode())[0],200)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":1}')[0],409)
            self.assertEqual(send(source,'/recovery/result',b'{"status":"conflict"}')[0],200)
            self.assertEqual(broker.wait_result(0),{'status':'conflict'})

    def test_previously_verified_source_preserves_divergent_target_without_claiming_identity(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,preserve_conflicts=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"local","key":"k","value":"old"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}:conflict".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            status,_,body=send(source,'/recovery/receipt',transfer['id'].encode())
            self.assertEqual((status,json.loads(body)),(200,{**transfer,'status':'preserved'}))
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":1}')[0],409)
            result={'status':'ok','copied':0,'identical':0,'preserved':1}
            self.assertEqual(send(source,'/recovery/result',json.dumps(result).encode())[0],200)
            self.assertEqual(broker.wait_result(0),result)

    def test_immutable_audio_conflict_is_never_auto_preserved(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True,
                                  result_source=source,preserve_conflicts=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            transfer=json.loads(send(source,'/recovery/stage',b'{"type":"audio","id":"fictif"}')[2])
            receipt=f"{transfer['id']}:{transfer['sha256']}:conflict".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            self.assertEqual(json.loads(send(source,'/recovery/receipt',transfer['id'].encode())[2])['status'],'conflict')
            self.assertEqual(send(source,'/recovery/result',b'{"status":"ok","copied":0,"identical":0,"preserved":1}')[0],409)

    def test_receipt_reports_conflict_without_losing_transfer_status(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            _,_,body=send(source,'/recovery/stage',b'donnee');transfer=json.loads(body)
            receipt=f"{transfer['id']}:{transfer['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':unknown')[0],409)
            self.assertEqual(send(destination,'/recovery/read')[2],b'donnee')
            self.assertEqual(send(destination,'/recovery/ack',receipt+b':conflict')[0],200)
            status,_,body=send(source,'/recovery/receipt',transfer['id'].encode())
            self.assertEqual((status,json.loads(body)),(200,{**transfer,'status':'conflict'}))

    def test_required_receipt_blocks_next_transfer_until_sender_reads_it(self):
        source,destination=available_ports()
        with PortalRecoveryBroker([source,destination],destination,ASSETS,require_receipt=True) as broker:
            def send(port,path,body=b''):
                return request(port,'POST',path,body,{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token})
            status,_,body=send(source,'/recovery/stage',b'premier');self.assertEqual(status,200)
            first=json.loads(body);receipt=f"{first['id']}:{first['sha256']}".encode()
            self.assertEqual(send(destination,'/recovery/ack',receipt)[0],200)
            self.assertEqual(send(source,'/recovery/stage',b'second')[0],409)
            for _ in range(2):
                status,_,body=send(source,'/recovery/receipt',first['id'].encode())
                self.assertEqual((status,json.loads(body)),(200,first))
            self.assertEqual(send(source,'/recovery/stage',b'second')[0],200)
            self.assertEqual(send(source,'/recovery/receipt',first['id'].encode())[0],404)

    def test_explicit_cross_engine_transfer_can_use_same_origin(self):
        port=available_ports(1)[0]
        with PortalRecoveryBroker([port],port,ASSETS,allow_same_origin_transfer=True) as broker:
            headers={'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token}
            status,_,body=request(port,'POST','/recovery/stage',b'donnees fictives',headers)
            self.assertEqual(status,200);prepared=json.loads(body)
            status,_,body=request(port,'POST','/recovery/read',b'',headers)
            self.assertEqual((status,body),(200,b'donnees fictives'))
            receipt=f"{prepared['id']}:{prepared['sha256']}".encode()
            self.assertEqual(request(port,'POST','/recovery/ack',receipt,headers)[0],200)
            self.assertEqual(request(port,'POST','/recovery/read',b'',headers)[0],404)

    def test_any_occupied_port_fails_closed_and_releases_partial_reservations(self):
        first = available_ports(1)[0]
        blocker = socket.socket()
        try:
            blocker.bind(('127.0.0.1', 0))
            blocker.listen()
            occupied = blocker.getsockname()[1]
            with self.assertRaises(RecoveryUnavailable):
                PortalRecoveryBroker([first, occupied], first, ASSETS)
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', first))
        finally:
            blocker.close()

    def test_close_stops_every_listener_and_releases_reserved_ports(self):
        ports = available_ports(10)
        broker = PortalRecoveryBroker(ports, ports[0], ASSETS).start()
        threads = tuple(broker._threads)
        broker.close()
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        for port in ports:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', port))

    def test_close_terminates_an_accepted_idle_connection(self):
        port = available_ports(1)[0]
        broker = PortalRecoveryBroker([port], port, ASSETS).start()
        self.addCleanup(broker.close)
        accepted = threading.Event()
        server = broker._servers[0]
        process_request = server.process_request
        def observe(connection, address):
            accepted.set()
            return process_request(connection, address)
        server.process_request = observe
        with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
            self.assertTrue(accepted.wait(2))
            broker.close()
            connection.settimeout(1)
            # A WebView may preconnect while a broker is active. The next
            # broker must never receive a request via that old connection.
            try:
                connection.sendall(b'GET /recovery HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n')
                data = connection.recv(1024)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                data = b''
            self.assertEqual(data, b'')

    def test_port_can_return_to_a_normal_relay_after_a_request(self):
        port = available_ports(1)[0]
        with PortalRecoveryBroker([port], port, ASSETS):
            self.assertEqual(request(port, 'GET', '/recovery')[0], 200)
        # ThreadingHTTPServer, used by the normal relay, enables SO_REUSEADDR.
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))
            probe.listen()

    def test_invalid_configuration_is_rejected(self):
        port = available_ports(1)[0]
        with self.assertRaises(ValueError): PortalRecoveryBroker([port, port], port, ASSETS)
        with self.assertRaises(ValueError): PortalRecoveryBroker([port], port + 1, ASSETS)
        with self.assertRaises(ValueError): PortalRecoveryBroker([port], port, {})


class RecoveryInventoryTransportTests(unittest.TestCase):
    headers = RecoveryBrokerTests.headers
    post = RecoveryBrokerTests.post

    def setUp(self):
        self.a, self.b = available_ports()
        self.plan = OriginInventoryPlan([self.a, self.b], default_port=self.a)
        self.broker = PortalRecoveryBroker([self.a, self.b], self.a, ASSETS, inventory_plan=self.plan).start()
        self.addCleanup(self.broker.close)

    def test_inventory_requires_all_ports_and_blocks_early_transfer(self):
        empty = json.dumps({'localEntries':0,'audioChunks':0}).encode()
        one = json.dumps({'localEntries':2,'audioChunks':1}).encode()
        self.assertEqual(self.post(self.b, '/recovery/stage', b'content')[0], 409)
        self.assertEqual(self.post(self.a, '/recovery/complete')[0], 409)
        self.assertIsNone(self.broker.wait_complete(0))
        self.assertEqual(self.post(self.b, '/recovery/inventory', one)[0], 400)
        status, _, initial = self.post(self.a, '/recovery/status')
        self.assertEqual((status,json.loads(initial)['nextPort']), (200,self.a))
        status, _, interim = self.post(self.a, '/recovery/inventory', empty)
        self.assertEqual((status,json.loads(interim)['state']), (200,'scanning'))
        status, _, done = self.post(self.b, '/recovery/inventory', one)
        self.assertEqual((status,json.loads(done)['state'],json.loads(done)['port']), (200,'ready',self.b))
        self.assertEqual(self.post(self.b, '/recovery/stage', b'content')[0], 409)
        self.assertEqual(self.post(self.a, '/recovery/complete')[0], 403)
        self.assertIsNone(self.broker.wait_complete(0))
        self.assertEqual(self.post(self.b, '/recovery/complete')[0], 200)
        self.assertEqual(self.broker.wait_complete(0), self.b)
        self.assertEqual(self.post(self.b, '/recovery/complete')[0], 200)

    def test_multiple_origins_are_not_silently_selected(self):
        payload = json.dumps({'localEntries':1,'audioChunks':0}).encode()
        self.post(self.a, '/recovery/inventory', payload)
        status, _, result = self.post(self.b, '/recovery/inventory', payload)
        self.assertEqual((status,json.loads(result)['state']), (200,'needsRecovery'))
        self.assertNotIn('port',json.loads(result))
        self.assertEqual(self.post(self.b, '/recovery/stage', b'content')[0], 200)
        self.assertEqual(self.post(self.a, '/recovery/complete')[0], 409)
        self.assertIsNone(self.broker.wait_complete(0))

    def test_unreadable_and_malformed_inventory_cannot_become_empty(self):
        duplicate = b'{"localEntries":0,"localEntries":1,"audioChunks":0}'
        self.assertEqual(self.post(self.a, '/recovery/inventory', duplicate)[0], 400)
        self.assertEqual(self.plan.status()['checked'],0)
        self.assertEqual(self.post(self.a, '/recovery/inventory', b'{"unavailable":true}')[0], 200)
        self.assertEqual(self.plan.status()['state'],'unavailable')
        self.assertEqual(self.post(self.b, '/recovery/stage', b'content')[0], 409)
        self.assertEqual(self.post(self.a, '/recovery/complete')[0], 409)

if __name__ == '__main__':
    unittest.main()
