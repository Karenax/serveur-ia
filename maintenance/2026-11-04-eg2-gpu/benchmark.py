"""Offline synthetic EG2 benchmark; never changes the production service."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def cases():
    paragraph=('Le projet prévoit une livraison en novembre. Les documents sont conservés '
        'sur le serveur. Un rappel permet de reprendre le dossier et de vérifier '
        'les décisions confirmées. Les sauvegardes protègent les informations. ')
    return [('query_short',['Comment retrouver les documents du projet ?'],'query'),
        ('documents_32',['Projet '+str(i)+'. Les documents sont sauvegardés sur le serveur Kiara.' for i in range(32)],'document'),
        ('long_4',[('Dossier '+str(i)+'. '+paragraph*25)[:4200] for i in range(4)],'document'),
        ('long_32',[('Dossier '+str(i)+'. '+paragraph*25)[:4200] for i in range(32)],'document')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--name',required=True)
    parser.add_argument('--gpu',default='')
    parser.add_argument('--dtype',choices=('float32','float16'),default='float32')
    parser.add_argument('--attention',choices=('eager','sdpa'),default='eager')
    parser.add_argument('--batch',type=int,default=4)
    parser.add_argument('--budget-mib',type=int,default=0)
    args=parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES=args.gpu,HF_HUB_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    import torch
    import numpy as np
    import psutil
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    gpu=bool(args.gpu);device='cuda:0' if gpu else 'cpu'
    report={'name':args.name,'device':device,'gpu_uuid':args.gpu,'dtype':args.dtype,
        'attention':args.attention,'batch':args.batch,'cpu_threads':2,'torch':torch.__version__,
        'cuda_build':torch.version.cuda,'cases':[],'synthetic_only':True}
    path=OUT/(args.name+'.json')
    def write():path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def sync():
        if gpu:torch.cuda.synchronize()
    def memory():
        result={'rss_mib':round(psutil.Process().memory_info().rss/2**20,1)}
        if gpu:
            free,total=torch.cuda.mem_get_info()
            result.update(allocated_mib=round(torch.cuda.memory_allocated()/2**20,1),
                reserved_mib=round(torch.cuda.memory_reserved()/2**20,1),
                peak_allocated_mib=round(torch.cuda.max_memory_allocated()/2**20,1),
                peak_reserved_mib=round(torch.cuda.max_memory_reserved()/2**20,1),
                driver_free_mib=round(free/2**20,1))
        return result
    try:
        if gpu:
            assert torch.cuda.is_available(),'CUDA unavailable'
            report['gpu_name']=torch.cuda.get_device_name(0)
            report['capability']=list(torch.cuda.get_device_capability(0))
            report['compiled_architectures']=torch.cuda.get_arch_list()
            total=torch.cuda.get_device_properties(0).total_memory
            torch.cuda.set_per_process_memory_fraction(args.budget_mib*2**20/total,0)
            report['allocator_budget_mib']=args.budget_mib
        started=time.monotonic()
        model=SentenceTransformer(str(ROOT/'toolchain/eg2-model'),device='cpu',local_files_only=True,
            trust_remote_code=False,config_kwargs={'vision_config':None,'audio_config':None},
            model_kwargs={'torch_dtype':getattr(torch,args.dtype),'attn_implementation':args.attention})
        model.max_seq_length=2048
        if gpu:model.to(device)
        sync()
        report['load_seconds']=round(time.monotonic()-started,3)
        report['parameters']=sum(p.numel() for p in model.parameters())
        report['after_load']=memory();write()
        print(args.name+': model loaded, '+str(report['parameters'])+' parameters.',flush=True)
        with torch.inference_mode():
            model.encode(['Vérification de démarrage.'],prompt='',batch_size=1,normalize_embeddings=True,show_progress_bar=False)
            sync()
            for name,texts,mode in cases():
                print(args.name+': '+name+' started.',flush=True)
                prompt='task: search result | query: ' if mode=='query' else ''
                tokens=int(model.tokenize([prompt+t for t in texts])['attention_mask'].sum().item())
                durations=[];vectors=None
                for _ in range(3 if name in ('query_short','documents_32') else 1):
                    sync();started=time.monotonic()
                    vectors=model.encode(texts,prompt=prompt,batch_size=args.batch,
                        normalize_embeddings=True,show_progress_bar=False)
                    sync();durations.append(time.monotonic()-started)
                vectors=np.asarray(vectors,dtype=np.float32)
                assert vectors.shape==(len(texts),768) and np.isfinite(vectors).all()
                norms=np.linalg.norm(vectors,axis=1)
                assert bool(((norms>.98)&(norms<1.02)).all()),'invalid normalization'
                row={'case':name,'texts':len(texts),'characters':len(texts[0]),'tokens':tokens,
                    'seconds':[round(v,4) for v in durations],
                    'median_seconds':round(statistics.median(durations),4),'memory':memory()}
                reference=OUT/('reference-'+name+'.npy')
                if args.name=='cpu_eager':np.save(reference,vectors)
                elif reference.is_file():
                    expected=np.load(reference)
                    similarities=np.sum(expected*vectors,axis=1)/(np.linalg.norm(expected,axis=1)*norms)
                    row['minimum_cosine_vs_cpu']=float(similarities.min())
                    row['maximum_absolute_delta']=float(np.max(np.abs(expected-vectors)))
                report['cases'].append(row);write()
                print(args.name+': '+name+' '+str(row['median_seconds'])+' seconds.',flush=True)
        report['passed']=True
    except Exception as error:
        report['passed']=False;report['error_type']=type(error).__name__;report['error']=str(error)[:2400]
        print(args.name+': '+report['error_type']+': '+str(error)[:700],flush=True)
    finally:write()
    if not report.get('passed'):raise SystemExit(1)


if __name__=='__main__':main()
