param([int]$ServerPid,[string]$OutputPath)
$rows=[System.Collections.Generic.List[object]]::new()
while($true){
 $p=Get-Process -Id $ServerPid -ErrorAction SilentlyContinue
 if(!$p){break}
 $rows.Add([pscustomobject]@{time=(Get-Date).ToString('o');ram_gib=$p.WorkingSet64/1GB;private_gib=$p.PrivateMemorySize64/1GB})
 $rows | ConvertTo-Json | Set-Content -LiteralPath $OutputPath -Encoding UTF8
 Start-Sleep -Milliseconds 1000
}

