"""EmbeddingGemma 2's documented context budget, including prompt and special tokens."""

MAX_INPUT_TOKENS = 8192
NO_TRUNCATION = {'text': {'truncation': False}}


class EmbeddingInputTooLong(ValueError):
    def __init__(self, index, tokens):
        self.index = index
        self.tokens = tokens
        super().__init__(f'Texte {index + 1} : {tokens} jetons ; maximum {MAX_INPUT_TOKENS}, préfixe compris. Aucun contenu tronqué.')


def input_tokens(model, texts, prompt):
    total = 0
    # Count each input separately to avoid padding an entire large batch.
    for index, text in enumerate(texts):
        features = model.tokenize([prompt + text], processing_kwargs=NO_TRUNCATION)
        count = int(features['attention_mask'].sum().item())
        if count > MAX_INPUT_TOKENS:
            raise EmbeddingInputTooLong(index, count)
        total += count
    return total
