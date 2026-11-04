"""Package only the reviewed client scripts, catalogue and guide; never any key."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES=('Installer-Codex-Kiara.ps1','Demarrer-Codex-Kiara.ps1',
       'Enregistrer-Cle-Codex-Kiara.ps1','Lire-Cle-Codex-Kiara.ps1','qwen-models.json','README.md')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'toolchain/releases-staging/codex-20261102/Codex-Kiara.zip')
    parser.add_argument('--reports',type=Path,default=ROOT/'toolchain/test-results/codex-20261102')
    args=parser.parse_args()
    for name in ('responses-tests.json','live-client.json','live-subagents.json','live-edit.json','app-server.json','app-server-dpapi.json','https-codex.json'):
        assert json.loads((args.reports/name).read_text(encoding='utf-8'))['passed'],name
    assert json.loads((args.reports/'deployment/verified.json').read_text(encoding='utf-8'))['passed']
    sources={name:(HERE/name).read_bytes() for name in FILES}
    manifest={'format':'kiara-codex-client','version':'2026-11-02','model':'fred-qwen',
              'endpoint':'https://ia.karenax.net/v1','codex_tested':'0.166.0-alpha.5.1',
              'files':{name:hashlib.sha256(data).hexdigest() for name,data in sources.items()},
              'verified':['responses-sse','client-function-tools','client-custom-apply-patch','two-qwen-subagents',
                          'app-server-multiple-turns','local-compaction','windows-dpapi-credential-helper','deployed-https']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sources.items(): archive.writestr('Codex-Kiara/'+name,data)
        archive.writestr('Codex-Kiara/manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
    with zipfile.ZipFile(args.output) as archive:
        assert sorted(archive.namelist())==sorted(['Codex-Kiara/'+name for name in FILES]+['Codex-Kiara/manifest.json'])
        for name,wanted in manifest['files'].items(): assert hashlib.sha256(archive.read('Codex-Kiara/'+name)).hexdigest()==wanted
    digest=hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.zip.sha256').write_text(digest+'  '+args.output.name+'\n',encoding='ascii')
    print(json.dumps({'artifact':str(args.output),'bytes':args.output.stat().st_size,'sha256':digest,'verified':True}))


if __name__=='__main__':main()
