"""Interpret symbol-level govulncheck JSON without treating exit zero as no findings."""
import argparse
import json
from pathlib import Path


def summarize(path):
    source=path.read_text(encoding='utf-8-sig');decoder=json.JSONDecoder();messages=[]
    while source.strip():
        value,end=decoder.raw_decode(source.lstrip());messages.append(value);source=source.lstrip()[end:]
    configs=[message['config'] for message in messages if 'config' in message]
    findings=[message['finding'] for message in messages if 'finding' in message]
    called=sorted({finding['osv'] for finding in findings if finding.get('trace') and finding['trace'][0].get('function')})
    if not configs:raise ValueError('Missing govulncheck configuration record')
    return {'passed':not called,'config':configs,'called_advisories':called,'finding_records':len(findings)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=summarize(args.input);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not result['passed']:raise SystemExit(1)
