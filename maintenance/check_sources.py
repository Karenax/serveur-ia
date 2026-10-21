"""Check current first-party Python/JavaScript/PowerShell sources without running them."""
import ast
import json
from pathlib import Path
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
listed=subprocess.check_output(['git','-C',str(ROOT),'ls-files','--cached','--others','--exclude-standard','-z',
    'lanceur','client-qwen','client-android','client-voice','maintenance','*.ps1']).decode().split('\0')
listed.extend(['preuves/conversation-windows-20261011/finalize.py',
               'recherche/strata-0.1.43.1-20261013/Comparer-Deux-Modeles.py'])
python_files=[];js_files=[];powershell_files=[]
with tempfile.TemporaryDirectory(prefix='fred-source-check-') as temporary:
    for name in sorted(set(filter(None,listed))):
        path=ROOT/name
        if not path.is_file():continue
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8-sig'),filename=name);python_files.append(name)
        elif path.suffix in ('.js','.cjs','.mjs','.html'):
            scripts=[path] if path.suffix!='.html' else []
            if path.suffix=='.html':
                for index,code in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>',path.read_text(encoding='utf-8'),re.S|re.I)):
                    if not code.strip():continue
                    output=Path(temporary)/(str(len(js_files))+'-'+str(index)+'.js');output.write_text(code.replace('__CONFIG__','{}'),encoding='utf-8');scripts.append(output)
            for script in scripts:
                result=subprocess.run(['node','--check',str(script)],capture_output=True,text=True)
                if result.returncode:raise ValueError(name+': '+result.stderr)
                js_files.append(name)
        elif path.suffix=='.ps1':powershell_files.append(name)
    script=Path(temporary)/'parse.ps1';sources=Path(temporary)/'paths.json';sources.write_text(json.dumps([str(ROOT/name) for name in powershell_files]),encoding='utf-8')
    script.write_text('''param([string]$Sources)
$files=Get-Content -LiteralPath $Sources -Raw | ConvertFrom-Json
$errorsFound=@()
foreach($file in $files){$tokens=$null;$parseErrors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$parseErrors);foreach($item in $parseErrors){$errorsFound+=@{file=$file;line=$item.Extent.StartLineNumber;message=$item.Message}}}
if($errorsFound.Count){$errorsFound|ConvertTo-Json -Depth 4;exit 1}
Write-Output "$($files.Count) PowerShell scripts parsed"
''',encoding='utf-8')
    engines={}
    for engine in ('pwsh','powershell.exe'):
        result=subprocess.run([engine,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-Sources',str(sources)],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if result.returncode:raise ValueError(engine+': '+result.stdout+result.stderr)
        engines[engine]=len(powershell_files)
print(json.dumps({'python_syntax':len(python_files),'javascript_syntax':len(js_files),'powershell_syntax':engines,'passed':True}))
