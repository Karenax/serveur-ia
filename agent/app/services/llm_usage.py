"""Request-local provider token measurements, never text-length estimates."""
from contextlib import contextmanager
from contextvars import ContextVar

_collection = ContextVar('llm_usage_collection', default=None)


def count(value):
    return value if type(value) is int and value >= 0 else None


def normalize(provider, payload):
    if not isinstance(payload, dict):
        return {'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None,
                'source': 'missing'}
    if provider == 'ollama':
        prompt, completion = count(payload.get('prompt_eval_count')), count(payload.get('eval_count'))
        total, source = None, 'ollama_counts'
    else:
        usage = payload.get('usage')
        usage = usage if isinstance(usage, dict) else {}
        prompt, completion = count(usage.get('prompt_tokens')), count(usage.get('completion_tokens'))
        total, source = count(usage.get('total_tokens')), 'openai_usage'
    if total is not None and prompt is not None and completion is not None and total != prompt+completion:
        return {'prompt_tokens': prompt, 'completion_tokens': completion, 'total_tokens': None,
                'source': source, 'inconsistent': True}
    derived = total is None and prompt is not None and completion is not None
    return {'prompt_tokens': prompt, 'completion_tokens': completion,
            'total_tokens': prompt+completion if derived else total, 'source': source,
            'total_formula': 'reported_prompt_plus_completion' if derived else 'provider_total'}


@contextmanager
def observe_request(provider, model):
    collection = _collection.get()
    if collection is None:
        yield lambda response: None
        return
    receipt = {'provider': provider, 'model': model, 'total_tokens': None, 'response_received': False}
    collection.append(receipt)
    def received(response):
        receipt.update(normalize(provider, response), response_received=True)
    try:
        yield received
    except Exception as error:
        receipt['error_type'] = type(error).__name__
        raise


@contextmanager
def collect():
    attempts = []
    token = _collection.set(attempts)
    try:
        yield attempts
    finally:
        _collection.reset(token)


def summarize(attempts):
    measured = [row['total_tokens'] for row in attempts if count(row.get('total_tokens')) is not None]
    complete = bool(attempts) and len(measured) == len(attempts)
    return {'attempts': attempts, 'measured_tokens': sum(measured) if measured else None,
            'complete': complete, 'measured_attempts': len(measured), 'total_attempts': len(attempts)}


def aggregate(answers):
    known, complete, partial = [], 0, 0
    for answer in answers:
        usage = answer.get('usage')
        if not isinstance(usage, dict) or count(usage.get('measured_tokens')) is None:
            continue
        known.append(usage['measured_tokens'])
        if usage.get('complete') is True:
            complete += 1
        else:
            partial += 1
    return {'tokens': sum(known) if known else None, 'token_complete_answers': complete,
            'token_partial_answers': partial, 'token_unmeasured_answers': len(answers)-complete-partial,
            'token_total_answers': len(answers)}
