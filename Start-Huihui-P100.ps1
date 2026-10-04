param([switch]$MTP,[int]$DraftTokens=2,[ValidateSet('layer','row','tensor')][string]$Split='layer',[ValidateSet('on','off')][string]$Flash='on',[ValidateSet('cafe','llama')][string]$Engine='cafe')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if(Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue){throw 'Port 8080 occupé'}
$env:PATH="$root\toolchain\cuda-12.4\bin;"+$env:PATH
$env:CUDA_VISIBLE_DEVICES='GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142'
$env:CUDA_DISABLE_PTX_JIT='1'
$exe="$root\cafe-build-p100\bin\llama-server.exe"
if($Engine -eq 'llama'){$exe="$root\llama-b11344\llama-server.exe"}
$model='D:\modèle\huihui-ai\Huihui-Qwen3.8-27B-abliterated-GGUF\Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf'
$mode=if($MTP){"mtp-$DraftTokens"}else{'sans-mtp'}
$mode="$mode-$Split-fa-$Flash"
if($Engine -eq 'llama'){$mode="llama-$mode"}
$a=@('-m',('"'+$model+'"'),'--host','127.0.0.1','--port','8080','--alias','huihui-27b','-c','4096','-np','1','-t','4','-tb','4','-b','512','-ub','256','-ngl','99','--fit','off','--split-mode',$Split,'--tensor-split','1,1','--flash-attn',$Flash,'--jinja','--metrics')
if($MTP){$a+=@('-md','"D:\modèle\huihui-ai\Huihui-Qwen3.8-27B-abliterated-GGUF\mtp-Qwen3.8-27B-Q4_0.gguf"','--spec-type','draft-mtp','--spec-draft-n-max',"$DraftTokens",'--spec-draft-ngl','99')}
$p=Start-Process -FilePath $exe -ArgumentList $a -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -RedirectStandardOutput "$root\huihui-$mode.stdout.log" -RedirectStandardError "$root\huihui-$mode.stderr.log" -PassThru
$p.Id|Set-Content "$root\huihui.pid"
@{mode=$mode;exe=$exe;model=$model;arguments=$a}|ConvertTo-Json -Depth 5|Set-Content "$root\huihui-configuration.json" -Encoding UTF8
Write-Output "Huihui $mode : PID $($p.Id)"


