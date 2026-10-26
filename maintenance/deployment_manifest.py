"""Bind component manifests and validation evidence into one deployment record."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_CHECKS={'sources','runtimes','server','windows','voice','android','ui','go','go-security','dependencies','maintenance','android-lint'}


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def generate(manifests,validation):
    evidence=json.loads(validation.read_text(encoding='utf-8'))
    if evidence.get('passed') is not True:raise ValueError('Deployment requires successful validation evidence')
    checked={value['check'] for value in evidence.get('results',[]) if value.get('passed') is True}
    if REQUIRED_CHECKS-checked:raise ValueError('Missing deployment checks: '+','.join(sorted(REQUIRED_CHECKS-checked)))
    components={}
    for path in manifests:
        data=json.loads(path.read_text(encoding='utf-8'))
        component=data.get('component')
        if data.get('version')!=2 or component not in {'server','windows','android','voice'}:
            raise ValueError('A scoped component manifest is required')
        if component in components:raise ValueError('Duplicate component: '+component)
        artifact=data['artifact']
        if Path(artifact['name']).name!=artifact['name']:raise ValueError('Invalid artifact name')
        binary=path.parent/artifact['name']
        if not binary.is_file() or binary.stat().st_size!=artifact['bytes'] or digest(binary)!=artifact['sha256']:
            raise ValueError('Artifact no longer matches its manifest: '+component)
        for name,expected in data['source_files'].items():
            source=(ROOT/name).resolve()
            if not source.is_relative_to(ROOT) or not source.is_file() or digest(source)!=expected:
                raise ValueError('Source changed since build: '+name)
        components[component]={'manifest':path.name,'sha256':digest(path),'artifact':data['artifact'],
                               'source_commit':data['source_commit'],'source_files':data['source_files']}
    return {'format':1,'created_at':datetime.now(timezone.utc).isoformat(),'components':components,
            'validation':{'file':validation.name,'sha256':digest(validation)}}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifests',type=Path,nargs='+',required=True)
    parser.add_argument('--validation',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=generate(args.manifests,args.validation)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Deployment manifest:',args.output)
