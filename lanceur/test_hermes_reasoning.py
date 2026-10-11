"""Exact reasoning controls and real native provider wire shapes without cloud cost."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from core import HIDDEN, write_json
from test_hermes_models import CloudFixture
from hermes_reasoning import controls, request_reasoning
from hermes_service import child_environment, installation


class ReasoningTests(unittest.TestCase):
    def test_none_and_graded_levels_are_exact_and_unknown_levels_fail(self):
        caps={'thinking':True,'reasoning_efforts':['high','none','medium'],'reasoning_mode':'effort'}
        self.assertEqual(controls(caps)['reasoning_efforts'],['none','medium','high'])
        for effort in ('none','medium','high'):
            request=request_reasoning({'reasoning_effort':effort},caps)
            self.assertEqual(request['model_options'],{'reasoning_effort':effort})
        for effort in ('low','max','xhigh','ultra','on'):
            with self.subTest(effort=effort),self.assertRaises(ValueError):request_reasoning({'reasoning_effort':effort},caps)
    def test_max_is_preserved_only_when_announced(self):
        caps={'thinking':True,'reasoning_efforts':['none','low','medium','high','xhigh','max']}
        self.assertEqual(request_reasoning({'reasoning_effort':'max'},caps)['model_options'],{'reasoning_effort':'max'})
        self.assertEqual(request_reasoning({'reasoning_effort':'maximum'},caps)['effort'],'max')
        self.assertNotIn('ultra',controls({**caps,'reasoning_efforts':['ultra','max']})['reasoning_efforts'])
    def test_toggle_is_explicit_structured_native_config_and_omission_is_unset(self):
        caps={'thinking':True,'reasoning_mode':'toggle','reasoning_efforts':['none','on']}
        self.assertEqual(request_reasoning({'reasoning_effort':'on'},caps)['model_options'],{'reasoning':{'enabled':True}})
        self.assertEqual(request_reasoning({'reasoning_effort':'none'},caps)['model_options'],{'reasoning_effort':'none'})
        self.assertEqual(request_reasoning({},caps),{'effort':None,'enabled':None,'model_options':{}})
        with self.assertRaises(ValueError):request_reasoning({'reasoning_effort':'high'},caps)
    def test_mandatory_and_uncontrollable_models_do_not_offer_fake_disable(self):
        mandatory={'thinking':True,'reasoning_efforts':['low','medium','high','max']}
        with self.assertRaises(ValueError):request_reasoning({'reasoning_effort':'none'},mandatory)
        uncontrolled={'thinking':True,'reasoning_mode':'none','reasoning_efforts':[]}
        self.assertEqual(request_reasoning({},uncontrolled)['model_options'],{})
        for effort in ('none','on','high'):
            with self.subTest(effort=effort),self.assertRaises(ValueError):request_reasoning({'reasoning_effort':effort},uncontrolled)
    def test_templates_are_consistent_and_fingerprint_intent_is_canonical(self):
        caps={'thinking':True,'reasoning_efforts':['none','low','medium','high','max']}
        self.assertEqual(request_reasoning({'chat_template_kwargs':{'reasoning_effort':'max','enable_thinking':True}},caps)['effort'],'max')
        for payload in ({'reasoning_effort':'max','chat_template_kwargs':{'enable_thinking':False}},
            {'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':True}},
            {'reasoning_effort':'high','chat_template_kwargs':{'reasoning_effort':'medium'}}):
            with self.subTest(payload=payload),self.assertRaises(ValueError):request_reasoning(payload,caps)


_SOURCE=Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'hermes/hermes-agent'
@unittest.skipUnless(os.name=='nt' and (_SOURCE/'hermes_cli/main.py').is_file(),'Installed native Hermes required.')
class NativeReasoningTests(unittest.TestCase):
    def test_openrouter_native_parser_profile_transport_and_sdk_preserve_exact_http_controls(self):
        cloud=CloudFixture()
        try:
            with tempfile.TemporaryDirectory(prefix='fred-native-reasoning-') as temporary:
                home=Path(temporary)
                write_json(home/'config.yaml',{'model':{'provider':'custom','default':'fixture','base_url':cloud.url}})
                runtime=installation()
                script=r'''
import contextlib,io,json,logging,sys
logging.disable(logging.CRITICAL)
data=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 from gateway.platforms.api_server import _request_reasoning_config
 from agent.transports.chat_completions import ChatCompletionsTransport
 from hermes_cli import models_reasoning_caps
 from providers import get_provider_profile
 from openai import OpenAI
 table={'nvidia/nemotron-3-ultra-550b-a55b:free':{'supports_reasoning':True,'mandatory':False,'supported_efforts':['high','medium']},
        'fixture-toggle':{'supports_reasoning':True,'mandatory':False,'supported_efforts':None},
        'openai/gpt-6-luna':{'supports_reasoning':True,'mandatory':False,'supported_efforts':['none','low','medium','high','xhigh','max']}}
 models_reasoning_caps.openrouter_model_reasoning_capabilities=lambda model,**kw:table.get(model)
 profile=get_provider_profile('openrouter');transport=ChatCompletionsTransport()
 client=OpenAI(base_url=data['url'],api_key='fixture-native-key')
 for model,options in data['cases']:
  config=_request_reasoning_config(options)
  kwargs=transport.build_kwargs(model,[{'role':'user','content':'Public synthetic fixture'}],
      provider_profile=profile,reasoning_config=config,supports_reasoning=True,
      base_url='https://openrouter.ai/api/v1',max_tokens=8)
  client.chat.completions.create(**kwargs)
 client.close()
print(json.dumps({'requests':len(data['cases'])}))
'''
                cases=[('nvidia/nemotron-3-ultra-550b-a55b:free',{'reasoning_effort':effort}) for effort in ('none','medium','high')]
                cases += [('fixture-toggle',{'reasoning':{'enabled':True}}),('openai/gpt-6-luna',{'reasoning_effort':'max'})]
                result=subprocess.run([str(runtime['python']),'-c',script],input=json.dumps({'url':cloud.url,'cases':cases}).encode(),
                    env=child_environment(home,runtime),cwd=runtime['source'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                    timeout=35,creationflags=HIDDEN)
                self.assertEqual(result.returncode,0,'Native reasoning fixture failed; private diagnostics suppressed.')
                self.assertEqual(json.loads(result.stdout)['requests'],5)
                self.assertEqual([body.get('reasoning') for _,_,body in cloud.calls],[
                    {'enabled':False},{'enabled':True,'effort':'medium'},{'enabled':True,'effort':'high'},
                    {'enabled':True},{'enabled':True,'effort':'max'}])
        finally:cloud.close()


if __name__=='__main__':unittest.main()
