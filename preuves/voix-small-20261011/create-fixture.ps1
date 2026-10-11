Add-Type -AssemblyName System.Speech
$voiceSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voiceSynth.GetInstalledVoices() | ForEach-Object { Write-Output $_.VoiceInfo.Name }
$voiceSynth.SelectVoice('Microsoft Hortense Desktop')
$voiceFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$voiceSynth.SetOutputToWaveFile((Join-Path $PSScriptRoot 'francais.wav'), $voiceFormat)
$voiceSynth.Speak('Bonjour Fred. Je souhaite préparer une réunion demain matin. Ajoute les documents du projet et résume les décisions importantes.')
$voiceSynth.Dispose()

