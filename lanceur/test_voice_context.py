"""The oral context limit preserves instructions, the current turn and stored data."""
from copy import deepcopy
import unittest
from voice_context import bounded_messages,compact_sources,context_budget,CAPACITY,INPUT_TOKENS,OUTPUT_TOKENS


class VoiceContextTests(unittest.TestCase):
    def test_context_uses_loaded_capacity_and_allows_100k_output(self):
        self.assertEqual(context_budget({'max_context':262144}),(262144,100000))
        self.assertEqual(context_budget({'max_context':131072}),(131072,65536))
        messages=[{'role':'user','content':'Une longue demande.'}]
        self.assertEqual(bounded_messages(messages,lambda _:100000),(messages,100000,0))

    def test_images_reserve_the_pinned_encoder_budget(self):
        from voice_context import image_budget,IMAGE_TOKENS
        messages=[{'role':'user','content':[{'type':'text','text':'Photo'},{'type':'image_url','image_url':{'url':'data:image/png;base64,fixture'}}]}]
        self.assertEqual(image_budget(messages),IMAGE_TOKENS)
        self.assertEqual(image_budget([{'role':'user','content':'Texte'}]),0)
    def test_short_input_stays_identical_and_reserves_output(self):
        messages=[{'role':'system','content':'Français.'},{'role':'user','content':'Bonjour.'}]
        result,tokens,removed=bounded_messages(messages,lambda _:30)
        self.assertIs(result,messages);self.assertEqual((tokens,removed),(30,0))
        self.assertEqual(CAPACITY,INPUT_TOKENS+OUTPUT_TOKENS)

    def test_oldest_complete_exchanges_are_omitted_without_changing_history(self):
        messages=[{'role':'system','content':'Consignes du projet.'}]
        for i in range(10):messages += [{'role':'user','content':str(i)*80},{'role':'assistant','content':str(i)*80}]
        messages += [{'role':'system','content':'Mémoire autorisée.'},{'role':'user','content':'Question actuelle.'}]
        before=deepcopy(messages);count=lambda rows:sum(len(m['content']) for m in rows)
        result,tokens,removed=bounded_messages(messages,count,limit=400)
        self.assertEqual(before,messages);self.assertLessEqual(tokens,400)
        self.assertEqual(removed%2,0);self.assertEqual(result[0],messages[0]);self.assertEqual(result[-2:],messages[-2:])
        self.assertEqual(result[1]['role'],'user');self.assertEqual(result[2]['role'],'assistant')
        self.assertGreater(count([messages[removed-1],messages[removed],*result]),400)

    def test_oversized_current_question_or_instructions_fail_without_truncation(self):
        messages=[{'role':'system','content':'Consigne indispensable.'},{'role':'user','content':'Question complète.'}]
        before=deepcopy(messages)
        with self.assertRaisesRegex(ValueError,'162 144'):bounded_messages(messages,lambda _:200000)
        self.assertEqual(before,messages)

    def test_source_prompt_has_one_passage_and_preserves_the_complete_reference(self):
        source={'source_id':'authorized','title':'Décision','text':'Montant 4200 euros.','passage':'Montant 4200 euros.','revision':'v1','version':'v1','role':'user','status':'current','page':4}
        before=deepcopy(source);result=compact_sources([source])[0]
        self.assertEqual(before,source);self.assertEqual(result['text'],source['text'])
        self.assertEqual(result['source_id'],source['source_id']);self.assertEqual(result['page'],4)
        self.assertNotIn('passage',result);self.assertNotIn('version',result)


if __name__=='__main__':unittest.main(verbosity=2)
