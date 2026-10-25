import unittest
from voice_response import Decoder,configure

class VoiceResponseTests(unittest.TestCase):
    def test_answer_streams_after_two_characters_at_every_fragment_boundary(self):
        answer='Bonjour ! L’été arrive. Une citation : "oui". À bientôt 👋'
        for size in (1,2,3,7,23,1000):
            decoder=Decoder();raw='R:'+answer;emitted=[]
            for i in range(0,len(raw),size):emitted.append(decoder.feed(raw[i:i+size]))
            self.assertEqual(''.join(emitted),answer);self.assertEqual(decoder.finish()['answer'],answer)
        decoder=Decoder();self.assertEqual(decoder.feed('R:Bonjour'),'Bonjour')

    def test_search_header_never_reaches_audio_and_query_is_bounded(self):
        decoder=Decoder();self.assertEqual(decoder.feed('W:météo Paris'),'')
        self.assertEqual(decoder.finish()['query'],'météo Paris')
        for raw in ('W:','W:privé\nsecret','W:'+'q'*503,'{"action":"search"}','```json\n'):
            decoder=Decoder()
            with self.assertRaises(ValueError):decoder.feed(raw);decoder.finish()

    def test_plain_numbers_and_natural_answers_remain_usable_without_a_header(self):
        for text in ('42','Bonjour, je vous écoute.','Rien de particulier.','Voilà la réponse.'):
            for size in (1,2,5):
                decoder=Decoder();parts=[]
                for i in range(0,len(text),size):parts.append(decoder.feed(text[i:i+size]))
                self.assertEqual(''.join(parts),text)
                self.assertEqual(decoder.finish(),{'action':'answer','query':'','answer':text})

    def test_reply_can_contain_quotes_colons_and_literal_routing_text(self):
        decoder=Decoder();text='La chaîne à afficher est « W:Paris ». R: est une autre chaîne.'
        self.assertEqual(decoder.feed('R:'+text),text);self.assertEqual(decoder.finish()['query'],'')

    def test_configuration_preserves_input_and_does_not_request_buffered_json(self):
        body={'model':'local','messages':[{'role':'system','content':'Instructions privées.'},{'role':'user','content':'Bonjour.'}],'max_tokens':512}
        actual=configure(body)
        self.assertEqual(body['messages'][0]['content'],'Instructions privées.')
        self.assertIn('Protocole vocal',actual['messages'][0]['content'])
        self.assertNotIn('tools',actual);self.assertNotIn('response_format',actual)
        self.assertEqual(actual['max_tokens'],512)
        self.assertIs(actual['strata_checkpoint'],True)
        self.assertEqual(actual['strata_prefix'],{'messages':1})
        body['messages'].extend([{'role':'assistant','content':'37'},{'role':'user','content':'Ajoute cinq.'}])
        self.assertEqual(configure(body)['strata_prefix'],{'messages':1})

if __name__=='__main__':unittest.main()
