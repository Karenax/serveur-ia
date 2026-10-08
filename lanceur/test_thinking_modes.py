"""Verify the advertised levels against Strata's request parser and template."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from core import ROOT
import test_remote as fixture
from chat_attachments import normalize_reasoning
sys.path.insert(0,str(ROOT/'Strata-src'))
from serve.frontend import effort_kwargs,openai_to_messages,anthropic_to_messages,ChatTemplate

class ThinkingTests(unittest.TestCase):
    setUp=fixture.RemoteTests.setUp
    tearDown=fixture.RemoteTests.tearDown
    request=fixture.RemoteTests.request

    def test_four_advertised_levels_reach_the_backend_and_render(self):
        with self.request('/v1/models') as response:modes=json.load(response)['data'][0]['capabilities']['reasoning_efforts']
        self.assertEqual(modes,['none','low','medium','high'])
        template=ChatTemplate(ROOT/'Strata-src/serve/chat_template.jinja')
        for mode in modes:
            with self.subTest(mode=mode):
                with self.request('/v1/chat/completions',{'messages':[{'role':'user','content':'Test'}],'reasoning_effort':mode}) as response:response.read()
                request=fixture.FakeModel.captured[-1][1]
                self.assertEqual(request['reasoning_effort'],mode)
                messages,tools,kwargs=openai_to_messages(request)
                self.assertTrue(template.render(messages,tools,**kwargs))
                self.assertEqual(kwargs,effort_kwargs(mode))
        before=len(fixture.FakeModel.captured)
        with self.assertRaises(urllib.error.HTTPError) as refused:self.request('/v1/chat/completions',{'messages':[{'role':'user','content':'Test'}],'reasoning_effort':'invented'})
        self.assertEqual(refused.exception.code,400)
        self.assertEqual(len(fixture.FakeModel.captured),before)

    def test_aliases_are_the_same_levels_and_preferences_survive(self):
        for alias in ['high','xhigh','max','maximum']:
            self.assertEqual(normalize_reasoning(alias),'high')
            self.assertEqual(effort_kwargs(alias),effort_kwargs('high'))
        path=Path(self.temporary.name)/'settings.dpapi'
        with patch.object(fixture.client,'settings_path',return_value=path):
            for mode in ['none','low','medium','high']:
                fixture.client.save_preferences(self.profile,{'thinking_effort':mode})
                self.assertEqual(fixture.client.client_settings(self.profile)['preferences']['thinking_effort'],mode)
            with self.assertRaises(ValueError):fixture.client.save_preferences(self.profile,{'thinking_effort':'max'})

    def test_context_uses_same_template_and_includes_project_files_and_thinking(self):
        template=ChatTemplate(ROOT/'Strata-src/serve/chat_template.jinja')
        project=self.store.workspace.action(self.access['id'],{'action':'project_create','title':'Contexte test'})['id']
        self.store.workspace.action(self.access['id'],{'action':'document_create','project':project,'title':'Document','text':'Contenu du projet'})
        for mode in ['none','low','medium','high']:
            payload={'messages':[{'role':'user','content':'Texte du fichier joint'},{'role':'assistant','content':'Réponse','reasoning_content':'Réflexion conservée'},{'role':'user','content':'Brouillon'}],'reasoning_effort':mode,'project_id':project}
            with self.request('/v1/context',payload) as response:result=json.load(response)
            self.assertGreater(result['tokens'],0);self.assertEqual(result['capacity'],262144)
            counted=fixture.FakeModel.captured[-1][1]
            original=dict(payload);original.pop('project_id')
            original['messages'],_=self.store.workspace.context(self.access['id'],original['messages'],project,None)
            messages,tools,kwargs=openai_to_messages(original)
            count_messages,count_tools,count_kwargs=anthropic_to_messages(counted)
            self.assertEqual(template.render(messages,tools,**kwargs),template.render(count_messages,count_tools,**count_kwargs))
        with self.assertRaises(urllib.error.HTTPError):self.request('/v1/context',{'messages':[{'role':'user','content':'Test'}],'reasoning_effort':'invalid'})
