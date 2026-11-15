"""The extracted public agent adapter preserves authenticated identity and masking."""
import json
import threading
import types
import unittest
import urllib.error

import test_notifications_transport as notification_transport


class AgentCommandAdapterTests(unittest.TestCase):
    setUp=notification_transport.NotificationTransportTests.setUp
    tearDown=notification_transport.NotificationTransportTests.tearDown
    request=notification_transport.NotificationTransportTests.request

    def test_authenticated_agent_dispatch_and_private_error_masking(self):
        calls=[]
        def action(owner,value):
            calls.append((owner,value))
            if value.get('action')=='broken':raise ValueError('SYNTHETIC_PRIVATE_DETAIL')
            return {'accepted':True}
        self.store.hermes=types.SimpleNamespace(action=action)
        result=self.request('/v1/agent/action',{'action':'state'})
        self.assertEqual(result,{'accepted':True})
        self.assertEqual(calls,[(self.first['id'],{'action':'state'})])
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.request('/v1/agent/action',{'action':'broken'})
        self.assertEqual(failure.exception.code,400)
        detail=failure.exception.read().decode('utf-8');failure.exception.close()
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL',detail)
        self.assertIn('message',json.loads(detail)['error'])
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.request('/v1/agent/action',{'action':'state'},headers={'Authorization':'Bearer invalid'})
        self.assertEqual(denied.exception.code,401);denied.exception.close()
        self.assertEqual(len(calls),2)

    def test_agent_project_search_can_authenticate_an_internal_request(self):
        def action(owner, value, prepared):
            identities = []
            worker = threading.Thread(target=lambda: identities.append(
                self.store.authenticate(self.first['token'])))
            worker.start()
            worker.join(1)
            self.assertEqual(identities, [owner])
            return {'sources': []}

        self.store.workspace.action = action
        for name in ('search', 'knowledge_search'):
            with self.subTest(action=name):
                result = self.request('/v1/workspace/action', {
                    'action': name,
                    'project': 'f84a8a99-b5b8-493e-95a5-533a095d20a7',
                    'query': 'essai',
                })
                self.assertEqual(result, {'sources': []})


if __name__=='__main__':unittest.main()
