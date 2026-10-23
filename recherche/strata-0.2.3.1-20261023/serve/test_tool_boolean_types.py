"""Boolean tool arguments: model spelling errors must not reach clients as strings."""
import json
import unittest

from serve.frontend import OutputParser, json_tool_call, parse_tool_call


SCHEMA = {"name": "subagent", "parameters": {"type": "object", "properties": {
    "background": {"type": "boolean"}, "prompt": {"type": "string"}}}}


def xml(value, name="background"):
    return f"<function=subagent>\n<parameter={name}>\n{value}\n</parameter>\n</function>"


class BooleanArguments(unittest.TestCase):
    def test_xml_spelling_and_quotes(self):
        for literal, expected in [('True', True), ('False', False), ('true', True), ('false', False),
                                  ('"True"', True), ('"False"', False), ('"true"', True), ('"false"', False)]:
            with self.subTest(literal=literal):
                value = parse_tool_call(xml(literal), SCHEMA).arguments['background']
                self.assertIs(value, expected)

    def test_string_and_unknown_fields_are_preserved(self):
        for literal in ('True', 'False', 'true', 'false', '"True"', ' True ', 'print(True)'):
            self.assertEqual(parse_tool_call(xml(literal, 'prompt'), SCHEMA).arguments['prompt'], literal)
        self.assertEqual(parse_tool_call(xml('True', 'unknown'), SCHEMA).arguments['unknown'], 'True')

    def test_no_truthiness_guessing(self):
        for literal in ('yes', 'no', '1', '0', 'null', 'some True text'):
            value = parse_tool_call(xml(literal), SCHEMA).arguments['background']
            self.assertNotIsInstance(value, bool)

    def test_json_nested_fields(self):
        schema = {"name": "subagent", "parameters": {"properties": {
            "background": {"type": "boolean"}, "prompt": {"type": "string"},
            "options": {"type": "object", "properties": {"enabled": {"type": "boolean"}}},
            "flags": {"type": "array", "items": {"type": "boolean"}}}}}
        raw = json.dumps({"name": "subagent", "arguments": {"background": "True", "prompt": "True",
                         "options": {"enabled": "False", "unknown": "True"}, "flags": ["True", "False"]}})
        call = json_tool_call(raw, {'subagent': schema})
        self.assertEqual(call.arguments, {'background': True, 'prompt': 'True',
            'options': {'enabled': False, 'unknown': 'True'}, 'flags': [True, False]})

    def test_nullable_boolean_and_string_union(self):
        for kind, normalize in [({'type': ['boolean', 'null']}, True),
                                ({'anyOf': [{'type': 'boolean'}, {'type': 'null'}]}, True),
                                ({'oneOf': [{'type': 'boolean'}, {'type': 'null'}]}, True),
                                ({'type': ['boolean', 'string']}, False),
                                ({'anyOf': [{'type': 'boolean'}, {'type': 'string'}]}, False)]:
            schema = {'name': 'subagent', 'parameters': {'properties': {'background': kind}}}
            value = parse_tool_call(xml('"True"'), schema).arguments['background']
            self.assertEqual(value, True if normalize else 'True')

    def test_streamed_json_matches_final_call_at_all_chunk_boundaries(self):
        for literal, expected in [('True', True), ('False', False), ('"True"', True), ('"False"', False)]:
            raw = '<tool_call>\n' + xml(literal) + '\n</tool_call>'
            for width in (1, 2, 7, len(raw)):
                for stream in (False, True):
                    with self.subTest(literal=literal, width=width, stream=stream):
                        parser = OutputParser(thinking=False, tools=[SCHEMA], stream_tools=stream)
                        events = []
                        for i in range(0, len(raw), width):
                            events += parser.feed(raw[i:i + width])
                        events += parser.finish('stop')
                        calls = [e.call for e in events if e.kind == 'tool_call']
                        self.assertEqual(len(calls), 1)
                        self.assertIs(calls[0].arguments['background'], expected)
                        if stream:
                            args = json.loads(''.join(e.text for e in events if e.kind == 'tool_args'))
                            self.assertIs(args['background'], expected)

    def test_http_openai_and_anthropic_stream_and_nonstream(self):
        from serve.test_server import UnfinishedToolCall
        helper = UnfinishedToolCall('test_parser')
        helper.PROPS = {'background': {'type': 'boolean'}, 'prompt': {'type': 'string'}}
        raw = '</think>\n\n<tool_call>\n<function=write>\n<parameter=background>\nTrue\n</parameter>\n' \
              '<parameter=prompt>\nTrue\n</parameter>\n</function>\n</tool_call>'
        answers = helper.answers(raw)
        for (protocol, stream), (_, args) in answers.items():
            with self.subTest(protocol=protocol, stream=stream):
                values = [args] if stream else args
                decoded = [json.loads(x) if isinstance(x, str) else x for x in values]
                self.assertEqual(decoded, [{'background': True, 'prompt': 'True'}])


if __name__ == '__main__':
    unittest.main()
