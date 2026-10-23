"""Recover JSON arguments inside XML function envelopes, never a phantom {}."""
import copy
import json
import unittest
import urllib.error
import urllib.request

from serve.frontend import OutputParser, parse_tool_call

SCHEMA = {'name': 'subagent', 'parameters': {'type': 'object', 'properties': {
    'agent': {'type': 'string'}, 'description': {'type': 'string'},
    'prompt': {'type': 'string'}, 'background': {'type': 'boolean'}},
    'required': ['agent', 'description', 'prompt']}}
ARGS = {'agent': 'explore', 'description': 'Analyser le frontend',
        'prompt': 'Lecture seule : texte <parameter=x> et </function> puis </tool_call>.',
        'background': 'True'}
EXPECTED = {**ARGS, 'background': True}


def body(args=ARGS, fenced=False):
    payload = json.dumps(args, ensure_ascii=False)
    if fenced:
        payload = '```json\n' + payload + '\n```'
    return '<function=subagent>\n' + payload + '\n</function>'


def parse(raw, width=1, stream=True, schema=SCHEMA, thinking=False, recover=False):
    parser = OutputParser(thinking=thinking, tools=[schema], stream_tools=stream, recover=recover)
    events = []
    for i in range(0, len(raw), width):
        events += parser.feed(raw[i:i + width])
    return events + parser.finish('stop')


class HybridArguments(unittest.TestCase):
    def test_direct_decode_preserves_json_and_literal_xml_in_strings(self):
        for fenced in (False, True):
            self.assertEqual(parse_tool_call(body(fenced=fenced), SCHEMA).arguments, EXPECTED)

    def test_mixed_call_all_fragment_boundaries_and_stream_modes(self):
        for fenced in (False, True):
            raw = '<tool_call>\n' + body(fenced=fenced) + '\n</tool_call>'
            for width in (1, 2, 7, len(raw)):
                for stream in (False, True):
                    with self.subTest(fenced=fenced, width=width, stream=stream):
                        events = parse(raw, width, stream)
                        self.assertEqual([e.call.arguments for e in events if e.kind == 'tool_call'], [EXPECTED])
                        self.assertFalse([e for e in events if e.kind in ('tool_start', 'tool_args')])
                        self.assertEqual(''.join(e.text for e in events if e.kind == 'content'), '')

    def test_hybrid_without_required_schema_also_never_streams_empty_object(self):
        schema = copy.deepcopy(SCHEMA)
        schema['parameters'].pop('required')
        events = parse('<tool_call>' + body() + '</tool_call>', schema=schema)
        self.assertEqual([e.call.arguments for e in events if e.kind == 'tool_call'], [EXPECTED])
        self.assertFalse([e for e in events if e.kind in ('tool_start', 'tool_args')])

    def test_required_xml_is_validated_before_any_tool_event(self):
        raw = '<tool_call><function=subagent>\n'
        raw += ''.join(f'<parameter={k}>\n{v}\n</parameter>\n' for k, v in
                       [('agent', 'explore'), ('description', 'Test'), ('prompt', 'Lecture seule')])
        raw += '</function></tool_call>'
        events = parse(raw)
        self.assertEqual([e.call.arguments for e in events if e.kind == 'tool_call'],
                         [{'agent': 'explore', 'description': 'Test', 'prompt': 'Lecture seule'}])
        self.assertFalse([e for e in events if e.kind in ('tool_start', 'tool_args')])

    def test_empty_or_partial_required_call_is_an_explicit_error_before_emission(self):
        for inner in ('<function=subagent></function>', body({}), body({'agent': 'explore'}),
                      '<function=subagent><parameter=agent>explore</parameter></function>'):
            for recover in (False, True):
                parser = OutputParser(thinking=False, tools=[SCHEMA], stream_tools=True, recover=recover)
                events = []
                with self.assertRaisesRegex(ValueError, 'missing required fields'):
                    for char in '<tool_call>' + inner + '</tool_call>':
                        events += parser.feed(char)
                    events += parser.finish('stop')
                self.assertFalse([e for e in events if e.kind in ('tool_start', 'tool_args', 'tool_call')])

    def test_json_recovery_checks_required_fields(self):
        raw = '<tool_call>' + json.dumps({'name': 'subagent', 'arguments': {}}) + '</tool_call>'
        with self.assertRaisesRegex(ValueError, 'agent, description, prompt'):
            parse(raw, recover=True)

    def test_no_argument_tool_remains_valid(self):
        schema = {'name': 'subagent', 'parameters': {'type': 'object', 'properties': {}}}
        events = parse('<tool_call><function=subagent></function></tool_call>', schema=schema)
        self.assertEqual([e.call.arguments for e in events if e.kind == 'tool_call'], [{}])

    def test_cut_hybrid_never_becomes_a_call(self):
        raw = '<tool_call><function=subagent>{"agent":"explore"'
        self.assertFalse([e for e in parse(raw) if e.kind in ('tool_start', 'tool_args', 'tool_call')])

    def test_bare_and_multiple_mixed_calls(self):
        bare = body() + '\n'
        self.assertEqual([e.call.arguments for e in parse(bare, recover=True) if e.kind == 'tool_call'], [EXPECTED])
        batch = '<tool_call>' + body() + '\n' + body() + '</tool_call>'
        self.assertEqual([e.call.arguments for e in parse(batch, recover=True) if e.kind == 'tool_call'],
                         [EXPECTED, EXPECTED])

    def test_mixed_call_in_reasoning_and_quoted_example(self):
        raw = '<tool_call>' + body() + '</tool_call>\n</think>\n'
        self.assertEqual([e.call.arguments for e in parse(raw, thinking=True) if e.kind == 'tool_call'], [EXPECTED])
        quoted = '```\n<tool_call>' + body({}) + '</tool_call>\n```\n</think>\nTexte'
        self.assertFalse([e for e in parse(quoted, thinking=True) if e.kind == 'tool_call'])

    def test_http_openai_anthropic_and_streaming(self):
        from serve.test_server import UnfinishedToolCall
        helper = UnfinishedToolCall('test_parser')
        helper.PROPS = SCHEMA['parameters']['properties']
        raw = '</think>\n<tool_call>' + body().replace('function=subagent', 'function=write') + '</tool_call>'
        for (api, stream), (finish, args) in helper.answers(raw, max_tokens=1000).items():
            with self.subTest(api=api, stream=stream):
                items = [args] if stream else args
                self.assertEqual([json.loads(v) if isinstance(v, str) else v for v in items], [EXPECTED])
                self.assertEqual(finish, 'tool_calls' if api == 'openai' else 'tool_use')

    def test_http_missing_required_fields_is_error_not_empty_invocation(self):
        from pathlib import Path
        from serve.server import ByteTokenizer, MockEngine, Service, serve
        from serve.frontend import ChatTemplate
        from serve.test_server import CTX
        tok = ByteTokenizer()
        script = '</think>\n<tool_call><function=subagent>{}</function></tool_call>'
        service = Service(MockEngine(tok, script, max_context=CTX), tok,
                          ChatTemplate(Path(__file__).parent / 'chat_template.jinja'))
        httpd = serve(service, port=0)
        try:
            for api, path in [('openai', '/v1/chat/completions'), ('anthropic', '/v1/messages')]:
                tools = ([{'type': 'function', 'function': SCHEMA}] if api == 'openai' else
                         [{'name': 'subagent', 'input_schema': SCHEMA['parameters']}])
                for stream in (False, True):
                    with self.subTest(api=api, stream=stream):
                        payload = {'model': 'test', 'max_tokens': 500, 'stream': stream, 'tools': tools,
                                   'messages': [{'role': 'user', 'content': 'Test'}]}
                        req = urllib.request.Request(f'http://127.0.0.1:{httpd.server_port}' + path,
                            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
                            'anthropic-version': '2023-06-01'})
                        if not stream:
                            with self.assertRaises(urllib.error.HTTPError) as caught:
                                urllib.request.urlopen(req, timeout=15)
                            self.assertEqual(caught.exception.code, 400)
                            message = json.load(caught.exception)['error']['message']
                            caught.exception.close()
                            self.assertIn('missing required fields: agent, description, prompt', message)
                        else:
                            with urllib.request.urlopen(req, timeout=15) as response:
                                raw = response.read().decode()
                            events = [json.loads(line[6:]) for line in raw.splitlines()
                                      if line.startswith('data: {')]
                            errors = [e for e in events if 'error' in e]
                            self.assertTrue(errors, raw)
                            self.assertIn('missing required fields', errors[0]['error']['message'])
                            self.assertNotIn('"tool_calls"', raw)
                            self.assertNotIn('"tool_use"', raw)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == '__main__':
    unittest.main()
