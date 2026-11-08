"""Untruncated accounting and exact model context boundaries."""
from types import SimpleNamespace
import unittest
from embedding_limits import input_tokens, EmbeddingInputTooLong, NO_TRUNCATION


class LimitsTests(unittest.TestCase):
    def model(self, counts):
        self.inputs = []
        def tokenize(texts, **kwargs):
            self.inputs.append(texts)
            self.assertEqual(kwargs['processing_kwargs'], NO_TRUNCATION)
            return {'attention_mask': SimpleNamespace(sum=lambda: SimpleNamespace(item=lambda: next(counts)))}
        return SimpleNamespace(tokenize=tokenize)

    def test_exact_limit_and_prompt(self):
        model = self.model(iter([8192, 3]))
        self.assertEqual(input_tokens(model, ['a', 'b'], 'prefix: '), 8195)
        self.assertEqual(self.inputs, [['prefix: a'], ['prefix: b']])

    def test_overflow_rejects_whole_batch(self):
        model = self.model(iter([10, 8193]))
        with self.assertRaises(EmbeddingInputTooLong) as caught:
            input_tokens(model, ['a', 'b'], '')
        self.assertEqual((caught.exception.index, caught.exception.tokens), (1, 8193))


if __name__ == '__main__':unittest.main()
