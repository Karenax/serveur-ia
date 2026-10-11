param()
$ErrorActionPreference='Stop'
$conversationRoot=Split-Path $PSScriptRoot -Parent
$conversationPython=Join-Path $conversationRoot 'toolchain/conversation-client-python/Scripts/python.exe'
if (!(Test-Path -LiteralPath $conversationPython)) { throw 'Environnement de compilation de conversation absent.' }
$conversationTarget=Join-Path $conversationRoot 'client-qwen/voice'
New-Item -ItemType Directory -Force -Path $conversationTarget | Out-Null
& $conversationPython -m PyInstaller --noconfirm --onedir --console --name conversation-worker --collect-all sherpa_onnx --collect-all onnxruntime --exclude-module scipy --exclude-module torch --distpath $conversationTarget --workpath (Join-Path $conversationRoot 'toolchain/conversation-build') --specpath (Join-Path $conversationRoot 'toolchain/conversation-build') (Join-Path $PSScriptRoot 'conversation_worker.py')
if ($LASTEXITCODE -ne 0) { throw 'Compilation du moteur de conversation impossible.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'conversation-models.json') -Destination $conversationTarget -Force
Copy-Item -LiteralPath (Join-Path $conversationRoot 'toolchain/voice-build-windows/fredaec.dll') -Destination $conversationTarget -Force
& $conversationPython (Join-Path $PSScriptRoot 'prepare_conversation_licenses.py')
if ($LASTEXITCODE -ne 0) { throw 'Notices de conversation incomplètes.' }
