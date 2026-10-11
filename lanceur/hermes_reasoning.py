"""Exact, model-scoped reasoning controls; never silently weaken an effort."""
from chat_attachments import CANONICAL_REASONING_EFFORTS, normalize_reasoning

LADDER=[effort for effort in CANONICAL_REASONING_EFFORTS if effort not in {'on','ultra'}]
MISSING=object()


def controls(value):
    value=value if isinstance(value,dict) else {}
    raw=value.get('reasoning_efforts')
    levels=[effort for effort in LADDER if isinstance(raw,list) and effort in raw]
    mode=value.get('reasoning_mode')
    if mode=='toggle':
        levels=[effort for effort in ('none','on') if isinstance(raw,list) and effort in raw]
    elif mode!='none':mode='effort' if levels else 'none'
    if mode=='none':levels=[]
    return {'thinking':value.get('thinking') is True,'reasoning_mode':mode,'reasoning_efforts':levels}


def request_reasoning(data, capabilities):
    """Validate explicit user controls and produce native Hermes model_options."""
    caps=controls(capabilities);template=data.get('chat_template_kwargs',{})
    template=template if isinstance(template,dict) else {}
    top=data.get('reasoning_effort',MISSING);nested=template.get('reasoning_effort',MISSING)
    effort=normalize_reasoning(top) if top is not MISSING else normalize_reasoning(nested) if nested is not MISSING else None
    if top is not MISSING and nested is not MISSING and normalize_reasoning(top)!=normalize_reasoning(nested):
        raise ValueError('Niveaux de réflexion contradictoires.')
    enabled=template.get('enable_thinking',MISSING)
    if enabled is not MISSING and type(enabled) is not bool:raise ValueError('Activation de réflexion invalide.')
    if enabled is False:
        if effort is not None and effort!='none':raise ValueError('Réflexion désactivée avec un niveau actif.')
        effort='none'
    elif enabled is True and effort=='none':raise ValueError('Réflexion activée avec le niveau none.')
    if effort is not None:
        if effort not in caps['reasoning_efforts']:
            raise ValueError('Ce niveau de réflexion n’est pas pris en charge par le modèle sélectionné.')
        options={'reasoning':{'enabled':True}} if effort=='on' else {'reasoning_effort':effort}
        return {'effort':effort,'enabled':effort!='none','model_options':options}
    if enabled is True:
        if not caps['reasoning_efforts'] or not caps['thinking']:raise ValueError('Ce modèle ne propose pas de réglage de réflexion.')
        return {'effort':None,'enabled':True,'model_options':{'reasoning':{'enabled':True}}}
    return {'effort':None,'enabled':None,'model_options':{}}


def enforce_local_reasoning(data, request):
    """Bind the private local inference request to the admitted user's choice."""
    if not request or request.get('enabled') is None:return data
    template=dict(data.get('chat_template_kwargs',{}))
    template['enable_thinking']=request['enabled']
    effort=request.get('effort')
    if effort is not None and effort!='on':
        data['reasoning_effort']=effort
        if effort!='none':template['reasoning_effort']=effort
        else:template.pop('reasoning_effort',None)
    data['chat_template_kwargs']=template
    return data
