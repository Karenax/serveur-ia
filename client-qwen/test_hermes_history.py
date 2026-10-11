"""Client-cache reconciliation for server-finalized Hermes turns."""
import copy
import unittest

import history_store
from history_sync import merge


class HermesHistoryTests(unittest.TestCase):
    def history(self, content='Réponse partielle', interrupted=True):
        return {'currentId':'conversation-a','conversations':[{'id':'conversation-a','title':'Question','messages':[
            {'role':'user','content':'Ma question','turn_id':'turn-1'},
            {'role':'assistant','content':content,'reasoning_content':'','turn_id':'turn-1',**({'interrupted':True} if interrupted else {})}]}]}

    def test_final_result_replaces_partial_without_a_duplicate_conversation(self):
        local=self.history();server=self.history('Résultat complet et vérifié',False)
        result,conflicts=merge(local,server,{})
        self.assertEqual(conflicts,0);self.assertEqual(result,server)

    def test_missing_answer_is_recovered_by_its_user_turn(self):
        local=self.history();local['conversations'][0]['messages'].pop()
        server=self.history('Résultat complet',False)
        result,conflicts=merge(local,server,{})
        self.assertEqual(conflicts,0);self.assertEqual(result,server)

    def test_same_turn_cannot_replace_a_changed_user_or_project(self):
        for key in ('user','project'):
            local=self.history();server=self.history('Réponse finale',False)
            if key=='user':server['conversations'][0]['messages'][0]['content']='Autre question'
            else:server['conversations'][0]['project_id']='a'*32
            result,conflicts=merge(local,server,{})
            self.assertEqual(conflicts,1);self.assertEqual(len(result['conversations']),2)

    def test_unrelated_offline_messages_are_preserved_as_a_copy(self):
        local=self.history();local['conversations'][0]['messages'].append({'role':'user','content':'Ajout hors ligne'})
        result,conflicts=merge(local,self.history('Réponse finale',False),{})
        self.assertEqual(conflicts,1);self.assertEqual(result['conversations'][1]['messages'][-1]['content'],'Ajout hors ligne')

    def test_turn_identifier_is_bounded_and_optional_for_old_history(self):
        value=self.history();history_store.validate(value)
        for invalid in (None,'bad/turn','a'*129):
            bad=copy.deepcopy(value);bad['conversations'][0]['messages'][0]['turn_id']=invalid
            with self.assertRaises(history_store.HistoryError):history_store.validate(bad)
        for message in value['conversations'][0]['messages']:message.pop('turn_id')
        history_store.validate(value)


if __name__=='__main__':unittest.main()
