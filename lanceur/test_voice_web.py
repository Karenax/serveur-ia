"""Oral search uses native web tools while keeping direct, cancellable Qwen output."""
import json
import secrets
import threading
import time
import unittest

import test_text_transform as fixtures
import test_voice_conversation as oral_fixtures
from voice_web_plan import decision,recent_dialogue


class DecisionTests(unittest.TestCase):
    def test_only_supported_semantic_decisions_and_bounded_queries_are_accepted(self):
        for action,query in (('answer',''),('clarify',''),('search','actualité IA')):
            self.assertEqual(decision({'action':action,'query':query}),{'action':action,'query':query})
        for value in ({'action':'terminal','query':'cmd'}, {'action':'search','query':''},
                      {'action':'answer','query':'unused'}, {'action':'search','query':'x'*501},
                      {'action':'search','query':'q','owner':'other'}, {'action':'search','query':7}):
            with self.subTest(value=str(value)[:80]),self.assertRaises(ValueError):decision(value)

    def test_private_instructions_never_enter_the_local_routing_dialogue(self):
        messages=[{'role':'system','content':'PRIVATE-DOCUMENT'},
                  {'role':'user','content':'Une ancienne question.'},
                  {'role':'assistant','content':'Une ancienne réponse.'},
                  {'role':'user','content':'Et les nouvelles du jour ?'}]
        result=recent_dialogue(messages)
        self.assertNotIn('PRIVATE-DOCUMENT',json.dumps(result))
        self.assertEqual(result[-1],messages[-1])


class WebFixture:
    def __init__(self):
        self.calls = []
        self.error = None
        self.empty = False
        self.block = False
        self.ready = threading.Event()
        self.stopped = threading.Event()

    def call(self, name, arguments, valid):
        self.calls.append((name, arguments))
        self.ready.set()
        if self.block:
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                if not valid():
                    self.stopped.set()
                    raise ValueError('private diagnostic')
                time.sleep(.02)
            raise TimeoutError('Fixture was not cancelled')
        if self.error:
            raise ValueError(self.error)
        if name == 'web_search':
            return {'success': True, 'data': {'web': [] if self.empty else [
                {'url': 'https://example.org/actualite', 'title': 'Source publique', 'description': 'Extrait public.'},
                {'url': 'http://127.0.0.1/private', 'description': 'PRIVATE-RESULT'}]}}
        return {'results': [
            {'url': 'https://example.org/actualite', 'title': 'Page publique', 'content': 'FAIT-PUBLIC-4200'},
            {'url': 'https://example.net/redirection', 'title': 'Redirection publique', 'content': 'AUTRE-FAIT-PUBLIC'},
            {'url': 'http://192.168.1.41/private', 'content': 'PRIVATE-PAGE'}]}


class VoiceWebHTTPTests(unittest.TestCase):
    tearDown = fixtures.TextTransformHTTPTests.tearDown
    post = fixtures.TextTransformHTTPTests.post
    worker = fixtures.TextTransformHTTPTests.worker
    settle = fixtures.TextTransformHTTPTests.settle
    body = staticmethod(oral_fixtures.VoiceConversationHTTPTests.body)

    def setUp(self):
        fixtures.TextTransformHTTPTests.setUp(self)
        self.web = WebFixture()
        self.store.voice_web.web = self.web
        self.voice_plan={'action':'search','query':'information publique vérifiable'}
        self.permission(self.a['id'], True)

    def permission(self, owner, enabled):
        with self.store.workspace.db() as db:
            db.execute('INSERT OR REPLACE INTO policies(owner,settings) VALUES(?,?)',
                       (owner, json.dumps({'web': enabled})))

    def search_body(self, request):
        value = self.body(request)
        value['messages'][-1]['content'] = 'Cherche sur Internet une information publique.'
        return value

    def test_search_and_extract_feed_one_direct_qwen_with_visible_sources(self):
        request = secrets.token_hex(16)
        value = self.search_body(request)
        value['messages'].insert(0, {'role': 'assistant', 'content': 'HISTORIQUE-PRIVE'})
        status, raw = self.post(value, request)
        self.assertEqual(status, 200)
        self.assertIn(b'[DONE]', raw)
        self.assertIn(b'workspace_sources', raw)
        self.assertIn('Lecture des sources', raw.decode())
        self.assertEqual([name for name, _ in self.web.calls], ['web_search', 'web_extract'])
        self.assertNotIn('HISTORIQUE-PRIVE', json.dumps(self.web.calls))
        self.assertEqual(len(self.captured), 1)
        data = self.captured[0][1]
        self.assertEqual(data['model'], 'actual-local')
        self.assertEqual(data['reasoning_effort'], 'none')
        self.assertEqual(data['max_tokens'], 100000)
        self.assertFalse(data['strata_mcp'])
        self.assertNotIn('tools', data)
        prompt = json.dumps(data, ensure_ascii=False)
        self.assertIn('FAIT-PUBLIC-4200', prompt)
        self.assertIn('retrieved', prompt)
        self.assertNotIn('PRIVATE-', prompt + raw.decode())
        self.assertLessEqual(sum(len(json.dumps(m)) for m in data['messages']) // 4 + 20, 162144)
        self.settle()

    def test_ordinary_oral_turn_does_not_call_any_web_provider(self):
        self.voice_plan={'action':'answer','query':''}
        request = secrets.token_hex(16)
        self.assertEqual(self.post(self.body(request), request)[0], 200)
        self.assertEqual(self.web.calls, [])
        self.assertEqual(len(self.captured), 1)
        self.settle()

    def test_semantic_selection_does_not_require_any_web_keyword(self):
        request=secrets.token_hex(16);value=self.body(request)
        value['messages'][-1]['content']='Quoi de neuf aujourd’hui dans l’IA ?'
        self.assertIn(b'[DONE]',self.post(value,request)[1])
        self.assertEqual(self.web.calls[0][1]['query'],self.voice_plan['query'])
        self.assertEqual(len(self.plan_captured),1)
        self.assertEqual(self.plan_captured[0]['reasoning_effort'],'none')
        self.assertEqual(self.plan_captured[0]['max_tokens'],-1)
        self.settle()

    def test_missing_subject_requests_clarification_without_search(self):
        self.voice_plan={'action':'clarify','query':''}
        request=secrets.token_hex(16)
        self.post(self.body(request),request)
        self.assertEqual(self.web.calls,[])
        self.assertIn('sujet manque',json.dumps(self.captured[-1][1],ensure_ascii=False))
        self.settle()

    def test_cancel_during_semantic_decision_stops_before_search_and_answer(self):
        self.block_planner=True
        request=secrets.token_hex(16)
        thread,results,errors=self.worker(self.search_body(request),request)
        try:
            self.assertTrue(self.model_ready.wait(3))
            self.post({'voice_conversation':True},request,path='/v1/cancel')
            thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
            self.assertEqual(self.web.calls,[]);self.assertEqual(self.captured,[])
        finally:self.model_release.set();thread.join(6)
        self.settle()

    def test_invalid_decision_does_not_fall_back_to_keywords_or_leak_details(self):
        self.voice_plan='not JSON SECRET-DIAGNOSTIC'
        request=secrets.token_hex(16)
        status,raw=self.post(self.search_body(request),request)
        self.assertEqual(status,200);self.assertIn(b'error',raw)
        self.assertNotIn(b'SECRET-DIAGNOSTIC',raw)
        self.assertEqual(self.web.calls,[]);self.assertEqual(self.captured,[])
        self.settle()

    def test_account_without_web_permission_cannot_search(self):
        request = secrets.token_hex(16)
        self.permission(self.a['id'], False)
        status, raw = self.post(self.search_body(request), request)
        self.assertEqual(status, 200)  # The SSE connection already started.
        self.assertIn(b'error', raw)
        self.assertEqual(self.web.calls, [])
        self.assertEqual(self.captured, [])
        self.settle()

    def test_failure_or_empty_results_are_honest_and_do_not_leak_diagnostics(self):
        for empty in (False, True):
            self.web.empty = empty
            self.web.error = None if empty else 'SECRET-KEY /private/path'
            request = secrets.token_hex(16)
            status, raw = self.post(self.search_body(request), request)
            self.assertEqual(status, 200)
            prompt = json.dumps(self.captured[-1][1], ensure_ascii=False)
            self.assertIn('aucun résultat' if empty else 'indisponible', prompt)
            self.assertNotIn('SECRET-KEY', prompt + raw.decode())
            self.assertNotIn(b'workspace_sources', raw)
            self.settle()

    def test_cancel_revocation_and_permission_change_stop_search_before_qwen(self):
        for action in ('cancel', 'permission', 'revocation'):
            with self.subTest(action=action):
                self.web.ready.clear(); self.web.stopped.clear(); self.web.block = True
                self.permission(self.a['id'], True)
                request = secrets.token_hex(16)
                thread, results, errors = self.worker(self.search_body(request), request)
                try:
                    self.assertTrue(self.web.ready.wait(3))
                    if action == 'cancel':
                        self.assertEqual(self.post({'voice_conversation': True}, request, path='/v1/cancel')[0], 200)
                    elif action == 'permission':
                        self.permission(self.a['id'], False)
                    else:
                        self.store.revoke(self.a['id'])
                    self.assertTrue(self.web.stopped.wait(3))
                    thread.join(3)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(errors, [])
                    self.assertNotIn(b'workspace_sources', results[0][1])
                    self.assertNotIn(b'private diagnostic', results[0][1])
                    self.assertEqual(self.captured, [])
                    self.settle()
                finally:
                    self.store.text_transforms.cancel(self.a['id'], request)
                    thread.join(6)

    def test_other_owner_cancellation_cannot_stop_this_search(self):
        request = secrets.token_hex(16)
        self.post({'voice_conversation': True}, request, self.b, path='/v1/cancel')
        self.assertIn(b'[DONE]', self.post(self.search_body(request), request)[1])
        self.assertEqual(len(self.captured), 1)
        self.settle()

    def test_web_permission_revoked_during_model_output_stops_delivery(self):
        self.block_after_headers = True
        request = secrets.token_hex(16)
        thread, results, errors = self.worker(self.search_body(request), request)
        try:
            self.assertTrue(self.model_ready.wait(5))
            self.permission(self.a['id'], False)
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertNotIn(b'Texte corrige', results[0][1])
        finally:
            self.model_release.set(); thread.join(6)
        self.settle()


if __name__ == '__main__':
    unittest.main(verbosity=2)
