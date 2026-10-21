param([string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent))
$ErrorActionPreference = 'Stop'
$target = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ($target -ne 'D:\Serveur IA') { throw 'Ce correctif cible uniquement le projet audité D:\Serveur IA.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$original = Get-Acl -LiteralPath $target
$snapshot = Join-Path $PSScriptRoot 'acl-racine-avant.json'
if (!(Test-Path -LiteralPath $snapshot)) {
    @{path=$target; sddl=$original.Sddl; owner=$original.Owner} | ConvertTo-Json | Set-Content -LiteralPath $snapshot -Encoding utf8
}
$permissions = New-Object System.Security.AccessControl.DirectorySecurity
$permissions.SetOwner($identity.User)
$permissions.SetAccessRuleProtection($true, $false)
foreach ($sid in @($identity.User.Value, 'S-1-5-18', 'S-1-5-32-544')) {
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        (New-Object System.Security.Principal.SecurityIdentifier($sid)),
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        ([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit),
        [System.Security.AccessControl.PropagationFlags]::None,
        [System.Security.AccessControl.AccessControlType]::Allow)
    $permissions.AddAccessRule($rule)
}
# Change the project root only; Windows propagates inheritance to its children.
# Existing protected private directories retain their own restrictive ACLs.
Set-Acl -LiteralPath $target -AclObject $permissions
$paths = @($target, (Join-Path $target 'lanceur\app.py'), (Join-Path $target 'lanceur\acces-distants.json'))
$checks = foreach ($path in $paths) {
    $acl = Get-Acl -LiteralPath $path
    $broad = @($acl.Access | Where-Object {
        $_.AccessControlType -eq 'Allow' -and
        $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -in @('S-1-1-0','S-1-5-11','S-1-5-32-545')
    })
    if ($broad.Count) { throw "Des droits trop larges subsistent : $path" }
    @{path=$path;sddl=$acl.Sddl;restricted=$true}
}
$checks | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'acl-apres.json') -Encoding utf8
Write-Output 'Droits du projet et des fichiers de contrôle restreints au propriétaire, SYSTEM et administrateurs.'
