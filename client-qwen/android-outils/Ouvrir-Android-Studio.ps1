param()
. (Join-Path $PSScriptRoot 'Environnement-Android.ps1')
$studio = Join-Path $racineProjet 'toolchain\android-studio\bin\studio64.exe'
if (!(Test-Path -LiteralPath $studio)) { throw 'Android Studio absent dans toolchain.' }
Start-Process -FilePath $studio -WindowStyle Normal
