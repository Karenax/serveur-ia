"""Real installed SDK/Hermes builders with synthetic JWTs and mocked HTTP only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from core import HIDDEN
from hermes_codex_compat import GATEWAY_BOOTSTRAP, PATCH_SOURCE
from hermes_service import child_environment, installation


_SDK_TESTS = r'''
import asyncio, base64, contextlib, io, json, logging, sys, unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from openai import OpenAI, AsyncOpenAI
logging.disable(logging.CRITICAL)
from agent import auxiliary_client as aux
from agent import agent_runtime_helpers as helpers
from agent.agent_init import _explicit_client_kwargs

OFFICIAL = 'https://chatgpt.com/backend-api/codex'

def jwt(account=None, region=None):
    auth = {}
    if account: auth['chatgpt_account_id'] = account
    if region: auth['chatgpt_data_residency'] = region
    payload = base64.urlsafe_b64encode(json.dumps({'https://api.openai.com/auth': auth}).encode()).decode().rstrip('=')
    return 'fixture.' + payload + '.fixture'

class Wire:
    def __init__(self):
        self.calls = []
        self.mints = []
        self.tokens = [jwt('fixture-A', 'eu'), jwt('fixture-B', 'us'), jwt()]
    def mint(self):
        token = self.tokens[len(self.mints) % len(self.tokens)]
        self.mints.append(token)
        return token
    def handle(self, request):
        # Comparing against the bearer on the wire catches an extra mint in
        # the shim as well as headers derived from a previous token.
        token = request.headers.get('Authorization', '').removeprefix('Bearer ')
        self.calls.append((dict(request.headers), token, json.loads(request.content)))
        response = {'id': 'resp_fixture', 'object': 'response', 'created_at': 1, 'status': 'completed',
            'model': 'fixture-codex', 'output': [{'id': 'msg_fixture', 'type': 'message', 'role': 'assistant',
                'status': 'completed', 'content': [{'type': 'output_text', 'text': 'Fixture final', 'annotations': []}]}],
            'usage': {'input_tokens': 2, 'output_tokens': 3, 'total_tokens': 5}}
        if self.calls[-1][2].get('stream'):
            events = [{'type': 'response.output_item.done', 'sequence_number': 0, 'output_index': 0, 'item': response['output'][0]},
                      {'type': 'response.completed', 'sequence_number': 1, 'response': response}]
            raw = ''.join('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n' for event in events)
            return httpx.Response(200, headers={'Content-Type': 'text/event-stream'}, text=raw)
        return httpx.Response(200, json=response)
    def sync_http(self): return httpx.Client(transport=httpx.MockTransport(self.handle), trust_env=False)
    def async_http(self): return httpx.AsyncClient(transport=httpx.MockTransport(self.handle), trust_env=False)

STALE = {'ChatGPT-Account-ID': 'stale-account', 'x-openai-internal-codex-residency': 'stale-region'}

class SDKContracts(unittest.TestCase):
    def assert_rotation(self, wire, count):
        self.assertEqual(len(wire.mints), count)
        self.assertEqual(len(wire.calls), count)
        for i, (headers, bearer, body) in enumerate(wire.calls):
            self.assertEqual(bearer, wire.tokens[i % 3])
            self.assertEqual(headers.get('chatgpt-account-id'), ('fixture-A', 'fixture-B', None)[i % 3])
            self.assertEqual(headers.get('x-openai-internal-codex-residency'), ('eu', 'us', None)[i % 3])
            self.assertEqual(headers.get('originator'), 'hermes-agent')
            self.assertTrue(headers.get('user-agent', '').startswith('HermesAgent/'))
            self.assertEqual(body['model'], 'fixture-codex')

    def test_main_builder_prepares_actual_bearer_before_headers_and_rotates(self):
        wire = Wire()
        agent = SimpleNamespace(provider='custom:fixture', _client_log_context=lambda: 'fixture')
        kwargs = _explicit_client_kwargs(agent, wire.mint, OFFICIAL, 5)
        kwargs['http_client'] = wire.sync_http()
        kwargs['default_headers'].update(STALE)
        with patch.object(helpers, '_ra', return_value=SimpleNamespace(logger=logging.getLogger('fixture'))):
            client = helpers.create_openai_client(agent, kwargs, reason='fixture', shared=True)
        try:
            # Header construction must not mint; the SDK owns that operation.
            self.assertEqual(wire.mints, [])
            for _ in range(3):
                reply = client.responses.create(model='fixture-codex', input='Fixture', extra_headers=STALE)
                self.assertEqual(reply.output_text, 'Fixture final')
            self.assert_rotation(wire, 3)
            self.assertEqual(client._custom_headers['ChatGPT-Account-ID'], 'stale-account')
        finally: client.close()

    def test_native_async_aux_rebuild_keeps_callable_and_refreshes_headers(self):
        wire = Wire()
        with patch.object(aux, '_openai_http_client_kwargs', return_value={}):
            sync = aux._create_openai_client(api_key=wire.mint, base_url=OFFICIAL,
                http_client=wire.sync_http(), default_headers=STALE)
        async def scenario():
            with patch.object(aux, '_openai_http_client_kwargs', return_value={'http_client': wire.async_http()}):
                client, model = aux._to_async_client(sync, 'fixture-codex')
            try:
                self.assertIsInstance(client, AsyncOpenAI)
                self.assertTrue(callable(client._api_key_provider))
                self.assertEqual(wire.mints, [])
                for _ in range(3):
                    reply = await client.responses.create(model=model, input='Fixture', extra_headers=STALE)
                    self.assertEqual(reply.output_text, 'Fixture final')
                self.assert_rotation(wire, 3)
            finally: await client.close()
        try: asyncio.run(scenario())
        finally: sync.close()

    def test_native_codex_auxiliary_sync_and_async_adapters_use_same_wire_headers(self):
        wire = Wire()
        with patch.object(aux, '_openai_http_client_kwargs', return_value={}):
            sdk = aux._create_openai_client(api_key=wire.mint, base_url=OFFICIAL,
                http_client=wire.sync_http(), default_headers=STALE)
        client = aux.CodexAuxiliaryClient(sdk, 'fixture-codex')
        try:
            self.assertEqual(wire.mints, [])
            reply = client.chat.completions.create(model='fixture-codex', messages=[{'role': 'user', 'content': 'Fixture'}])
            self.assertEqual(reply.choices[0].message.content, 'Fixture final')
            async def scenario():
                twin = aux.AsyncCodexAuxiliaryClient(client)
                reply = await twin.chat.completions.create(model='fixture-codex', messages=[{'role': 'user', 'content': 'Fixture'}])
                self.assertEqual(reply.choices[0].message.content, 'Fixture final')
            asyncio.run(scenario())
            self.assert_rotation(wire, 2)
        finally: sdk.close()

    def test_other_provider_urls_and_official_lookalikes_are_unchanged(self):
        endpoints = ['https://api.githubcopilot.com', 'https://api.openai.com/v1',
            'http://127.0.0.1:8080/v1', 'https://proxy.invalid/backend-api/codex',
            'https://chatgpt.com.evil.invalid/backend-api/codex',
            'https://chatgpt.com:8443/backend-api/codex', 'https://chatgpt.com/backend-api/other',
            'http://chatgpt.com/backend-api/codex']
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                wire = Wire()
                configured = {**STALE, 'User-Agent': 'fixture-client', 'originator': 'fixture-originator'}
                client = OpenAI(api_key=wire.mint, base_url=endpoint, default_headers=configured,
                    http_client=wire.sync_http(), max_retries=0)
                try:
                    client.responses.create(model='fixture-codex', input='Fixture')
                    self.assertEqual(len(wire.mints), 1)
                    actual = wire.calls[0][0]
                    for name, value in configured.items(): self.assertEqual(actual[name.lower()], value)
                finally: client.close()

    def test_request_url_must_also_be_official(self):
        wire = Wire()
        client = OpenAI(api_key=wire.mint, base_url=OFFICIAL, default_headers=STALE,
            http_client=wire.sync_http(), max_retries=0)
        try:
            client.post('https://proxy.invalid/backend-api/codex/responses', cast_to=dict[str, object],
                        body={'model': 'fixture-codex'})
            self.assertEqual(wire.calls[0][0]['chatgpt-account-id'], 'stale-account')
        finally: client.close()

    def test_install_is_idempotent_without_changing_the_token_provider(self):
        sync_hook, async_hook = OpenAI._prepare_request, AsyncOpenAI._prepare_request
        _fred_install_codex_headers()
        self.assertIs(OpenAI._prepare_request, sync_hook)
        self.assertIs(AsyncOpenAI._prepare_request, async_hook)
        wire = Wire()
        client = OpenAI(api_key=wire.mint, base_url=OFFICIAL, http_client=wire.sync_http(), max_retries=0)
        try:
            client.responses.create(model='fixture-codex', input='Fixture')
            self.assert_rotation(wire, 1)
        finally: client.close()

selected = json.load(sys.stdin)['test']
suite = unittest.TestSuite([SDKContracts(selected)])
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
if not result.wasSuccessful():
    for _, failure in result.errors + result.failures: print(failure, file=sys.stderr)
    raise SystemExit(1)
print(json.dumps({'test': selected, 'passed': result.testsRun}))
'''


_SOURCE = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hermes/hermes-agent'


@unittest.skipUnless(os.name == 'nt' and (_SOURCE / 'hermes_cli/main.py').is_file(),
                     'Installed Windows Hermes SDK required.')
class CodexCompatibilityTests(unittest.TestCase):
    def native(self, code, *, test=None, arguments=()):
        runtime = installation()
        with tempfile.TemporaryDirectory(prefix='fred-codex-compat-') as temporary:
            result = subprocess.run([str(runtime['python']), '-c', code, *arguments],
                input=json.dumps({'test': test}).encode(), cwd=runtime['source'],
                env=child_environment(Path(temporary), runtime), capture_output=True,
                timeout=40, creationflags=HIDDEN)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace')[-5000:])
        return json.loads(result.stdout)

    def scenario(self, name):
        result = self.native(PATCH_SOURCE + '\n_fred_install_codex_headers()\n' + _SDK_TESTS, test=name)
        self.assertEqual(result, {'test': name, 'passed': 1})

    def test_main_builder_rotation(self):
        self.scenario('test_main_builder_prepares_actual_bearer_before_headers_and_rotates')

    def test_async_auxiliary_rebuild_rotation(self):
        self.scenario('test_native_async_aux_rebuild_keeps_callable_and_refreshes_headers')

    def test_native_codex_auxiliary_adapters(self):
        self.scenario('test_native_codex_auxiliary_sync_and_async_adapters_use_same_wire_headers')

    def test_other_providers_unchanged(self):
        self.scenario('test_other_provider_urls_and_official_lookalikes_are_unchanged')

    def test_request_url_scope(self):
        self.scenario('test_request_url_must_also_be_official')

    def test_idempotent_install(self):
        self.scenario('test_install_is_idempotent_without_changing_the_token_provider')

    def test_gateway_bootstrap_installs_before_entrypoint_and_keeps_arguments(self):
        prelude = '''
import json, runpy, sys
from openai import OpenAI, AsyncOpenAI
assert not getattr(OpenAI._prepare_request, '_fred_codex_headers', False)
def entrypoint(name, *, run_name, alter_sys):
    assert name == 'hermes_cli.main' and run_name == '__main__' and alter_sys
    assert getattr(OpenAI._prepare_request, '_fred_codex_headers', False)
    assert getattr(AsyncOpenAI._prepare_request, '_fred_codex_headers', False)
    print(json.dumps({'args': sys.argv[1:], 'installed': True}))
runpy.run_module = entrypoint
'''
        arguments = ('gateway', 'run', '--external-supervisor')
        self.assertEqual(self.native(prelude + GATEWAY_BOOTSTRAP, arguments=arguments),
                         {'args': list(arguments), 'installed': True})


if __name__ == '__main__':
    unittest.main()
