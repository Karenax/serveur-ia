"""Create a source-only server release; private data and runtimes stay external."""
import argparse
from pathlib import Path
import zipfile
from build_manifest import ROOT,generate,source_names
import json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    artifact=args.output/'kiara-server-sources.zip'
    with zipfile.ZipFile(artifact,'w',compression=zipfile.ZIP_DEFLATED) as packed:
        for name in source_names('server'):packed.write(ROOT/name,name)
        for name in ('RECONSTRUIRE-FRED.md','ARCHITECTURE-ACTUELLE.md','dependances/verrous/manifest.json',
                     'dependances/verrous/strata.requirements.txt','dependances/verrous/hermes-fred.requirements.txt',
                     'dependances/verrous/voix-serveur.requirements.txt','dependances/verrous/eg2.requirements.txt'):
            packed.write(ROOT/name,name)
    report=generate(artifact,'server');report['artifact']['kind']='sources-only'
    (args.output/'build-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(artifact)


if __name__=='__main__':main()
