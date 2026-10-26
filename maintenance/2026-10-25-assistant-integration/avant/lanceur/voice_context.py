"""Bound oral requests without changing the stored history or the engine's capacity."""
import http.client
import json

CAPACITY=16384
OUTPUT_TOKENS=512
INPUT_TOKENS=CAPACITY-OUTPUT_TOKENS


def compact_sources(sources):
    # The UI keeps the complete references. The prompt needs each passage once,
    # rather than both `text` and `passage` plus duplicate status/version fields.
    fields=('source_id','kind','title','text','role','page','revision')
    return [{k:source[k] for k in fields if source.get(k) is not None} for source in sources]


def token_count(port,model,key,messages):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
    try:
        headers={'Content-Type':'application/json'}
        if key:headers['Authorization']='Bearer '+key
        # Strata uses the same chat template and tokenizer for text messages on
        # both APIs, including late system turns. Preserve message order.
        body={'model':model,'messages':messages,'thinking':{'type':'disabled'},'strata_mcp':False}
        connection.request('POST','/v1/messages/count_tokens',json.dumps(body).encode(),headers)
        response=connection.getresponse();result=json.loads(response.read())
        count=result.get('input_tokens')
        if response.status!=200 or type(count) is not int or count<0:raise ValueError('Comptage du contexte vocal indisponible. Réessayez.')
        return count
    finally:connection.close()


def bounded_messages(messages,count,limit=INPUT_TOKENS):
    tokens=count(messages)
    if tokens<=limit:return messages,tokens,0
    last_user=max((i for i,m in enumerate(messages) if m['role']=='user'),default=len(messages)-1)
    # Remove complete oldest exchanges. System/project/source instructions and
    # the current question remain intact; the encrypted history is untouched.
    groups=[]
    for index,message in enumerate(messages[:last_user]):
        if message['role']=='system':continue
        if message['role']=='user' or not groups:groups.append([])
        groups[-1].append(index)
    def candidate(removed):
        skipped={index for group in groups[:removed] for index in group}
        return [message for i,message in enumerate(messages) if i not in skipped]
    minimum=candidate(len(groups));minimum_tokens=count(minimum)
    if minimum_tokens>limit:raise ValueError('La demande et les consignes dépassent le contexte vocal de 16 384 tokens. Raccourcissez le texte ou utilisez la conversation écrite.')
    low=1;high=len(groups);best=minimum;best_tokens=minimum_tokens
    while low<=high:
        middle=(low+high)//2;value=candidate(middle);size=count(value)
        if size<=limit:best=value;best_tokens=size;high=middle-1
        else:low=middle+1
    return best,best_tokens,len(messages)-len(best)
