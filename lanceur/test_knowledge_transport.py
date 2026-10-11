"""Existing client chat contract automatically recalls the authorized knowledge space."""
import json
import unittest
import urllib.request
import test_remote_sources_revocation as fence
import test_knowledge as fixtures
from knowledge import Knowledge


class KnowledgeTransportTests(unittest.TestCase):
    def setUp(self):
        fence.SourceAccessFenceTests.setUp(self)
        self.engine = fixtures.FixtureEngine()
        self.knowledge = Knowledge(self.store.workspace, self.engine)
        self.store.workspace.knowledge = self.knowledge
        self.store.workspace.action(self.access['id'], {'action': 'personal_memory_create',
            'text': 'Je préfère les repas végétariens.'})
        self.knowledge.synchronize()

    def tearDown(self):
        self.store.workspace.shutdown()
        fence.SourceAccessFenceTests.tearDown(self)

    def chat(self, project=None, query='repas végétariens'):
        payload = {'messages': [{'role': 'user', 'content': query}], 'stream': True}
        if project: payload['project_id'] = project
        request = urllib.request.Request('http://127.0.0.1:' + str(self.gateway.server_port) + '/v1/chat/completions',
            json.dumps(payload).encode(), {'Authorization': 'Bearer ' + self.access['token'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode()

    def test_outside_project_recall_and_sources_reach_existing_chat_contract(self):
        stream = self.chat()
        self.assertIn('workspace_sources', stream)
        content = json.dumps(self.captured[-1]['messages'], ensure_ascii=False)
        self.assertIn('repas végétariens', content)
        self.assertNotIn('Andromède', content)
        stream = self.chat(self.project, 'Andromède')
        content = json.dumps(self.captured[-1]['messages'], ensure_ascii=False)
        self.assertIn('Andromède', content)
        self.assertNotIn('végétariens', content)
        self.assertIn('workspace_sources', stream)

    def test_stopped_engine_keeps_lexical_memory_and_generation_working(self):
        self.engine.state = 'arrete'
        stream = self.chat()
        self.assertIn('workspace_sources', stream)
        self.assertIn('Resultat isole', stream)
        self.assertIn('végétariens', json.dumps(self.captured[-1]['messages'], ensure_ascii=False))


if __name__ == '__main__': unittest.main()
