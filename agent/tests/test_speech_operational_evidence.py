from copy import deepcopy
import json

import pytest

from app.services import speech_acceleration as acceleration
from app.services.speech_acceleration import validate_operational_evidence as validate
from scripts.speech_runtime import profile_key


@pytest.fixture
def evidence():
    profile={'model':'medium','model_directory':'FICTITIOUS-NOT-A-MODEL',
        'device':'cuda','device_index':0,'compute_type':'int8_float16','cpu_threads':4,
        'num_workers':1,'runtime_version':'1.2.1','local_files_only':True,'beam_size':5}
    requested={key:profile[key] for key in ['model_directory','device','device_index',
        'compute_type','cpu_threads','num_workers','local_files_only']}
    return {'schema':'agent-speech-operational-evidence-v1','model':'medium',
        'operational_pipeline_passed':True,'resident_and_owned_Job_closed':True,
        'industrial_quality_qualified':False,'physical_microphone_test':False,
        'physical_capture_qualified':False,'qualified_live_latency':False,
        'model_sha256':'a'*64,'model_identity':{'size':1234,'mtime_ns':5678,'config_sha256':'b'*64},
        'runtime_profile':profile,'runtime_profile_key':profile_key(profile),
        'actual_native_constructor':{'requested':requested,
            'native':{'device':'cuda','compute_type':'int8_float16','device_index':[0],'num_workers':1},
            'versions':{'faster_whisper':'1.2.1','ctranslate2':'4.8.2'}},
        'population':{'fictitious_utterances':15,'actual_visible_text_receipts':15,
            'stored_and_processed_packets':26}}


def check(evidence, **kwargs):
    return validate(evidence, model_identity=kwargs.get('model_identity',evidence['model_identity']),
        runtime_profile=kwargs.get('runtime_profile',evidence['runtime_profile']))


def test_actual_retained_SQL_GPU_pipeline_is_operational_without_hardware_or_quality_PASS(evidence):
    result=check(evidence)
    assert result['operational_pipeline_test_passed']
    assert result['validation_scope']=='fictitious_integrated_pipeline'
    assert not result['industrial_quality_qualified'] and not result['physical_capture_qualified']
    assert not result['qualified_live_latency']


def test_model_replacement_and_other_current_profile_cannot_reuse_receipt(evidence):
    identity={**evidence['model_identity'],'mtime_ns':evidence['model_identity']['mtime_ns']+1}
    assert check(evidence,model_identity=identity) is None
    profile={**evidence['runtime_profile'],'beam_size':10}
    assert check(evidence,runtime_profile=profile) is None


@pytest.mark.parametrize('field,value',[
    ('schema','legacy-CPU-physical'),('operational_pipeline_passed',1),
    ('operational_pipeline_passed',False),('resident_and_owned_Job_closed',False),
    ('industrial_quality_qualified',True),('physical_microphone_test',True),
    ('physical_capture_qualified',True),('qualified_live_latency',True),
    ('model_sha256','not-a-digest'),('runtime_profile_key','stale-key'),
])
def test_scope_or_identity_mismatch_does_not_promote_an_operational_sample(evidence,field,value):
    evidence[field]=value
    assert check(evidence) is None


@pytest.mark.parametrize('field,value',[('device','cpu'),('compute_type','float16'),('device_index',[1])])
def test_contradictory_actual_constructor_is_refused(evidence,field,value):
    evidence['actual_native_constructor']['native'][field]=value
    assert check(evidence) is None


@pytest.mark.parametrize('field,value',[('fictitious_utterances',0),('actual_visible_text_receipts',14),
    ('stored_and_processed_packets',-1),('actual_visible_text_receipts',True)])
def test_incomplete_or_invalid_population_is_refused(evidence,field,value):
    evidence['population'][field]=value
    assert check(evidence) is None


def test_unrelated_passed_metadata_does_not_qualify_physical_capture(evidence):
    extra=deepcopy(evidence)
    extra['passed']=True
    result=check(extra)
    assert result['operational_pipeline_test_passed'] and not result['physical_capture_qualified']
    assert not result['industrial_quality_qualified']


@pytest.fixture
def registered(evidence,tmp_path,monkeypatch):
    monkeypatch.setattr(acceleration,'BUNDLE',tmp_path)
    monkeypatch.delenv('PB_SPEECH_QUALIFICATION_REPORT',raising=False)
    (tmp_path/'operational-evidence-active.json').write_text(json.dumps(evidence))
    return {'installed':True,'ready':False,'loaded':False,'runtime_profile':evidence['runtime_profile'],
        'industrial_quality_qualified':False,'qualified_live_latency':False}


def test_GPU_operational_sample_marks_trial_ready_without_loading_or_qualifying_capture(registered,evidence):
    before=deepcopy(registered)
    result=acceleration.operational_readiness(registered,evidence['model_identity'])
    assert registered==before
    assert result['ready'] and result['real_test_passed'] and result['real_test_model']=='medium'
    assert not result['loaded'] and not result['physical_microphone_test_passed']
    assert not result['industrial_quality_qualified'] and not result['qualified_live_latency']
    assert result['validation_scope']=='fictitious_integrated_pipeline'


def test_evidence_does_not_hide_a_failed_current_installation(registered,evidence):
    registered['installed']=False
    result=acceleration.operational_readiness(registered,evidence['model_identity'])
    assert result is registered and not result['ready']


def test_existing_CPU_physical_receipt_is_never_replaced_by_GPU_evidence(registered,evidence):
    registered.update(ready=True,physical_microphone_test_passed=True,runtime_profile={'device':'cpu'})
    assert acceleration.operational_readiness(registered,evidence['model_identity']) is registered
    assert registered['physical_microphone_test_passed']


def test_explicit_qualification_override_preserves_operator_and_test_isolation(registered,evidence,monkeypatch):
    monkeypatch.setenv('PB_SPEECH_QUALIFICATION_REPORT','EXPLICIT-OTHER-RECEIPT.json')
    result=acceleration.operational_readiness(registered,evidence['model_identity'])
    assert result is registered and not result['ready']


def test_malformed_evidence_leaves_trial_unverified_without_breaking_status(registered,evidence,tmp_path):
    (tmp_path/'operational-evidence-active.json').write_text('not-json')
    result=acceleration.operational_readiness(registered,evidence['model_identity'])
    assert result is registered and not result['ready']
