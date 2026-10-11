function Invoke-FredAndroidSigning {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$PythonExecutable,
        [Parameter(Mandatory = $true)][string]$UnsignedApk,
        [Parameter(Mandatory = $true)][string]$AlignedApk,
        [Parameter(Mandatory = $true)][string]$SignedApk,
        [string]$SigningDirectory
    )
    $ErrorActionPreference = 'Stop'
    if (!$SigningDirectory) { $SigningDirectory = Join-Path $ProjectRoot 'toolchain\android-signing' }
    $SigningDirectory = [System.IO.Path]::GetFullPath($SigningDirectory)
    $keystore = Join-Path $SigningDirectory 'fred-client.p12'
    $passwordFile = Join-Path $SigningDirectory 'password.dpapi'
    $keytool = Join-Path $env:JAVA_HOME 'bin\keytool.exe'
    $buildTools = Join-Path $env:ANDROID_HOME 'build-tools\36.0.0'
    $zipalign = Join-Path $buildTools 'zipalign.exe'
    $apksigner = Join-Path $buildTools 'apksigner.bat'
    foreach ($tool in @($keytool, $zipalign, $apksigner, $UnsignedApk)) {
        if (!(Test-Path -LiteralPath $tool -PathType Leaf)) { throw "Fichier de signature absent : $tool" }
    }
    if ((Test-Path -LiteralPath $keystore) -and !(Test-Path -LiteralPath $passwordFile)) {
        throw 'Le mot de passe DPAPI de la cle Android manque. Ne pas remplacer la cle existante.'
    }
    & $PythonExecutable (Join-Path $PSScriptRoot 'Protect-Signing-Directory.py') $SigningDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Dossier de signature Android non prive.' }

    if (!(Test-Path -LiteralPath $passwordFile)) {
        $randomBytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
        $newPassword = [Convert]::ToBase64String($randomBytes)
        $securePassword = ConvertTo-SecureString -String $newPassword -AsPlainText -Force
        $encryptedPassword = ConvertFrom-SecureString -SecureString $securePassword
        $passwordTemporary = Join-Path $SigningDirectory ([Guid]::NewGuid().ToString('N') + '.dpapi.tmp')
        try {
            [System.IO.File]::WriteAllText($passwordTemporary, $encryptedPassword, [System.Text.Encoding]::ASCII)
            Move-Item -LiteralPath $passwordTemporary -Destination $passwordFile
        } finally {
            if (Test-Path -LiteralPath $passwordTemporary) { Remove-Item -LiteralPath $passwordTemporary }
            $newPassword = $null
            $encryptedPassword = $null
            [Array]::Clear($randomBytes, 0, $randomBytes.Length)
            $securePassword.Dispose()
        }
    }
    try {
        $savedPassword = [System.IO.File]::ReadAllText($passwordFile, [System.Text.Encoding]::ASCII)
        $decryptedPassword = ConvertTo-SecureString -String $savedPassword
    } catch {
        throw 'Le mot de passe de signature ne peut pas etre ouvert par cet utilisateur Windows.'
    }
    $pointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($decryptedPassword)
    try {
        $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $decryptedPassword.Dispose()
        $savedPassword = $null
    }
    $oldPasswordEnvironment = [Environment]::GetEnvironmentVariable('FRED_ANDROID_SIGN_PASSWORD', 'Process')
    try {
        # Only a process environment variable carries the password to the JDK tools.
        [Environment]::SetEnvironmentVariable('FRED_ANDROID_SIGN_PASSWORD', $plainPassword, 'Process')
        if (!(Test-Path -LiteralPath $keystore)) {
            $keystoreTemporary = Join-Path $SigningDirectory ([Guid]::NewGuid().ToString('N') + '.p12')
            try {
                & $keytool -genkeypair -alias fred-client -keystore $keystoreTemporary -storetype PKCS12 -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Acces Serveur Fred Android' -storepass:env FRED_ANDROID_SIGN_PASSWORD -keypass:env FRED_ANDROID_SIGN_PASSWORD -noprompt
                if ($LASTEXITCODE -ne 0) { throw 'Creation de la cle de signature Android impossible.' }
                Move-Item -LiteralPath $keystoreTemporary -Destination $keystore
            } finally {
                if (Test-Path -LiteralPath $keystoreTemporary) { Remove-Item -LiteralPath $keystoreTemporary }
            }
        }
        & $zipalign -f -P 16 4 $UnsignedApk $AlignedApk
        if ($LASTEXITCODE -ne 0) { throw 'Alignement APK impossible.' }
        & $apksigner sign --ks $keystore --ks-type PKCS12 --ks-key-alias fred-client --ks-pass env:FRED_ANDROID_SIGN_PASSWORD --key-pass env:FRED_ANDROID_SIGN_PASSWORD --out $SignedApk $AlignedApk
        if ($LASTEXITCODE -ne 0) { throw 'Signature APK impossible.' }
        & $apksigner verify --verbose --print-certs $SignedApk
        if ($LASTEXITCODE -ne 0) { throw 'Verification de la signature APK en echec.' }
        & $zipalign -c -P 16 4 $SignedApk
        if ($LASTEXITCODE -ne 0) { throw 'Verification de l alignement APK en echec.' }
    } finally {
        if ($null -eq $oldPasswordEnvironment) {
            Remove-Item -LiteralPath 'Env:\FRED_ANDROID_SIGN_PASSWORD' -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable('FRED_ANDROID_SIGN_PASSWORD', $oldPasswordEnvironment, 'Process')
        }
        $plainPassword = $null
        $oldPasswordEnvironment = $null
    }
}
