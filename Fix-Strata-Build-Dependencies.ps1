$ErrorActionPreference = 'Stop'
# Existing CMake compiler probes recorded a misencoded French /showIncludes prefix.
# This installation only contains the French compiler resources; VSLANG falls back
# to those resources. Store its actual UTF-8 prefix rather than CMake's mojibake.
$nbsp = [char]160
$prefix = "Remarque${nbsp}: inclusion du fichier${nbsp}:  "
$compilerResources = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\1033'
if (Test-Path -LiteralPath $compilerResources) { $prefix = 'Note: including file: ' }
$probeDirectory = Join-Path $PSScriptRoot 'strata-build-p100\CMakeFiles\3.31.8'
if (Test-Path -LiteralPath $probeDirectory) {
    foreach ($file in Get-ChildItem -LiteralPath $probeDirectory -Filter '*Compiler.cmake' -File) {
        $source = [IO.File]::ReadAllText($file.FullName)
        $fixed = [regex]::Replace($source, '(?m)^set\((CMAKE_\w+_CL_SHOWINCLUDES_PREFIX) "[^"\r\n]*"\)', ('set($1 "' + $prefix + '")'))
        if ($fixed -ne $source) { [IO.File]::WriteAllText($file.FullName, $fixed, [Text.UTF8Encoding]::new($false)) }
    }
}
# Objects built before the correction have empty dependency records. Rebuild
# those sources once so subsequent header edits are tracked normally by Ninja.
$ninja = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
$buildDirectory = Join-Path $PSScriptRoot 'strata-build-p100'
if ((Test-Path -LiteralPath $ninja) -and (Test-Path -LiteralPath (Join-Path $buildDirectory '.ninja_deps'))) {
    $records = & $ninja -C $buildDirectory -t deps
    if ($LASTEXITCODE) { throw 'Impossible de lire les dépendances Ninja.' }
    $changed = 0
    foreach ($line in $records) {
        if ($line -match '^CMakeFiles[/\\][^/\\]+\.dir[/\\]((?:src|tests)[/\\].+\.cpp)\.obj: #deps 0,') {
            $sourcePath = Join-Path (Join-Path $PSScriptRoot 'Strata-src') $Matches[1]
            if (Test-Path -LiteralPath $sourcePath) {
                (Get-Item -LiteralPath $sourcePath).LastWriteTime = Get-Date
                $changed++
            }
        }
    }
    Write-Output "Dépendances corrigées ; $changed sources sans suivi seront reconstruites."
}
