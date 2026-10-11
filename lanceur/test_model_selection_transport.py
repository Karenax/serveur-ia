"""Authenticated model selection over HTTP, with a disconnected local engine."""
import json
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from remote import AccessStore, serve_gateway
from workspace import Denied


class ModelSelectionTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-model-selection-')
        self.store = AccessStore(self.tmp.name)
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.access = self.store.issue('Temporary model selector')
        self.calls = []
        self.cloud_caps={'vision':False,'context_length':32000,'thinking':True,
                         'reasoning_mode':'effort','reasoning_efforts':['none','medium','high']}
        parent = self

        class Agent:
            def select_model(self, owner, requested=None):
                if requested == 'forbidden': raise Denied('Ce modèle n’est pas autorisé.')
                if requested not in (None, 'fred-qwen', 'cloud-test'): raise ValueError('Modèle inconnu.')
                return {'id': requested or 'fred-qwen', 'local': requested != 'cloud-test',
                        'capabilities': dict(parent.cloud_caps)}

            def model_catalog(self, owner):
                return {'object': 'list', 'default_model': 'fred-qwen', 'source': 'hermes', 'data': [
                    {'id': 'fred-qwen', 'label': 'Qwen local', 'available': False},
                    {'id': 'cloud-test', 'label': 'Connected provider', 'available': True}]}

            def stream(self, owner, data, *args):
                parent.calls.append((owner, data))
                yield b'data: {"choices":[{"delta":{"content":"Chosen model response"}}]}\n\n'
                yield b'data: [DONE]\n\n'

        self.store.hermes = Agent()
        self.health = patch('remote.health', return_value={'loaded': False}).start()
        self.gateway = serve_gateway(self.store, lambda: (1, 'legacy-local', ''), 0)
        self.thread = threading.Thread(target=self.gateway.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.gateway.shutdown(); self.gateway.server_close(); self.thread.join(3)
        patch.stopall()
        self.store.workspace.shutdown(); self.store.voice.close()
        self.tmp.cleanup()

    def call(self, path='/v1/models', value=None, token=None):
        headers = {'Authorization': 'Bearer ' + (token or self.access['token'])}
        if value is not None: headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(f'http://127.0.0.1:{self.gateway.server_port}' + path,
                                     json.dumps(value).encode() if value is not None else None, headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response: return response.status, response.read()
        except urllib.error.HTTPError as response:
            try: return response.code, response.read()
            finally: response.close()

    @staticmethod
    def body(model):
        return {'model': model, 'conversation_id': 'isolated', 'turn_id': secrets.token_hex(16),
                'messages': [{'role': 'user', 'content': 'Bonjour'}], 'stream': True}

    def test_catalog_survives_local_engine_unloaded_and_requires_auth(self):
        code, raw = self.call()
        self.assertEqual(200, code)
        catalog = json.loads(raw)
        self.assertEqual('hermes', catalog['source']); self.assertEqual('fred-qwen', catalog['default_model'])
        self.assertFalse(catalog['data'][0]['available']); self.assertTrue(catalog['data'][1]['available'])
        self.health.assert_not_called()
        self.assertEqual(401, self.call(token='invalid-access')[0])

    def test_cloud_turn_uses_selected_model_without_local_health(self):
        code, raw = self.call('/v1/chat/completions', self.body('cloud-test'))
        self.assertEqual(200, code); self.assertIn(b'[DONE]', raw)
        self.assertEqual(self.access['id'], self.calls[0][0]); self.assertEqual('cloud-test', self.calls[0][1]['model'])
        self.health.assert_not_called()

    def test_unavailable_local_unknown_and_forbidden_do_not_start_run(self):
        self.assertEqual(503, self.call('/v1/chat/completions', self.body('fred-qwen'))[0])
        self.assertEqual(400, self.call('/v1/chat/completions', self.body('invented'))[0])
        self.assertEqual(403, self.call('/v1/chat/completions', self.body('forbidden'))[0])
        self.assertEqual([], self.calls)

    def test_cloud_context_is_explicit_estimate_without_inference(self):
        code, raw = self.call('/v1/context', self.body('cloud-test'))
        self.assertEqual(200, code)
        context = json.loads(raw)
        self.assertTrue(context['estimated']); self.assertEqual(32000, context['capacity'])
        self.assertEqual('cloud-test', context['model']); self.assertEqual('visible_history', context['scope'])
        self.assertEqual([], self.calls); self.health.assert_not_called()

    def test_image_is_rejected_for_selected_model_without_vision(self):
        value = self.body('cloud-test')
        value['messages'][0]['content'] = [{'type': 'text', 'text': 'Image'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,iVBORw0KGgo='}}]
        code, raw = self.call('/v1/chat/completions', value)
        self.assertEqual(400, code); self.assertEqual([], self.calls)
        self.assertEqual('image_not_supported', json.loads(raw)['error']['code'])
    def test_nemotron_levels_are_exact_and_max_is_rejected_before_agent(self):
        for effort in ('none','medium','high'):
            with self.subTest(effort=effort):
                value={**self.body('cloud-test'),'reasoning_effort':effort}
                self.assertEqual(self.call('/v1/chat/completions',value)[0],200)
                self.assertEqual(self.calls[-1][1]['reasoning_effort'],effort)
        before=len(self.calls)
        for effort in ('max','low','xhigh'):
            with self.subTest(effort=effort):
                self.assertEqual(self.call('/v1/chat/completions',{**self.body('cloud-test'),'reasoning_effort':effort})[0],400)
        self.assertEqual(len(self.calls),before)
    def test_max_model_preserves_canonical_level_and_conflicting_template_is_rejected(self):
        self.cloud_caps['reasoning_efforts']=['none','low','medium','high','xhigh','max']
        value={**self.body('cloud-test'),'reasoning_effort':'max',
            'chat_template_kwargs':{'enable_thinking':True,'reasoning_effort':'max'}}
        self.assertEqual(self.call('/v1/chat/completions',value)[0],200)
        self.assertEqual(self.calls[-1][1]['reasoning_effort'],'max')
        self.assertEqual(self.calls[-1][1]['chat_template_kwargs']['reasoning_effort'],'max')
        before=len(self.calls);value['chat_template_kwargs']['enable_thinking']=False
        self.assertEqual(self.call('/v1/chat/completions',value)[0],400)
        self.assertEqual(len(self.calls),before)
    def test_mandatory_reasoning_rejects_disable_and_toggle_on_is_not_downgraded(self):
        self.cloud_caps['reasoning_efforts']=['low','medium','high','max']
        self.assertEqual(self.call('/v1/chat/completions',{**self.body('cloud-test'),'reasoning_effort':'none'})[0],400)
        self.cloud_caps.update(reasoning_mode='toggle',reasoning_efforts=['none','on'])
        self.assertEqual(self.call('/v1/chat/completions',{**self.body('cloud-test'),'reasoning_effort':'on'})[0],200)
        self.assertEqual(self.calls[-1][1]['reasoning_effort'],'on')


if __name__ == '__main__': unittest.main()
