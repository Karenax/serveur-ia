param()
$ErrorActionPreference = 'Stop'
$voiceRoot = Split-Path $PSScriptRoot -Parent
$voiceBuild = Join-Path $voiceRoot 'toolchain\voice-build-windows'
$voiceTarget = Join-Path $voiceRoot 'client-qwen\voice'
New-Item -ItemType Directory -Force -Path $voiceTarget | Out-Null
foreach ($voiceLicense in @('whisper.cpp-LICENSE.txt','ggml-LICENSE.txt','whisper-model-LICENSE.txt','llamafile-LICENSE.txt')) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot ('licenses\' + $voiceLicense)) -PathType Leaf)) { throw 'Licence vocale absente.' }
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'model.json') -Destination $voiceTarget -Force
Copy-Item -LiteralPath (Join-Path $voiceBuild 'fredvoice.dll') -Destination $voiceTarget -Force
Copy-Item -LiteralPath (Join-Path $voiceBuild 'fredaec.dll') -Destination $voiceTarget -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'conversation-models.json') -Destination $voiceTarget -Force
Get-ChildItem -LiteralPath (Join-Path $voiceBuild 'bin') -Filter '*.dll' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $voiceTarget -Force }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'licenses') -Destination $voiceTarget -Recurse -Force
$voiceSources = @{}
foreach ($voiceSource in @('model.json','conversation-models.json','CMakeLists.txt','fred_voice.cpp','fred_voice.h','fred_voice_jni.cpp','fred_aec.cpp','conversation_worker.py','turn_features.py','aec_capture.py')) {
    $voiceSources[$voiceSource] = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $voiceSource) -Algorithm SHA256).Hash.ToLowerInvariant()
}
@{engine='whisper.cpp';version='1.9.5';sources=$voiceSources;cpu_only=$true} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $voiceTarget 'build-info.json') -Encoding utf8
$voiceIndex = @{}
Get-ChildItem -LiteralPath $voiceTarget -File -Recurse | Where-Object { $_.Name -ne 'native-manifest.json' } | ForEach-Object { $voiceRelative = $_.FullName.Substring($voiceTarget.Length + 1).Replace('\','/'); $voiceIndex[$voiceRelative] = @{bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()} }
$voiceIndex | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $voiceTarget 'native-manifest.json') -Encoding utf8
