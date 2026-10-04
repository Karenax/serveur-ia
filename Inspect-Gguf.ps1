param([string]$Path)
$r = [IO.BinaryReader]::new([IO.File]::OpenRead($Path))
function Read-Str { $n=$r.ReadUInt64(); [Text.Encoding]::UTF8.GetString($r.ReadBytes([int]$n)) }
function Read-Val([int]$t) {
 switch($t) {
  0 { $r.ReadByte() } 1 { $r.ReadSByte() } 2 { $r.ReadUInt16() } 3 { $r.ReadInt16() }
  4 { $r.ReadUInt32() } 5 { $r.ReadInt32() } 6 { $r.ReadSingle() } 7 { $r.ReadBoolean() }
  8 { Read-Str } 9 { $at=$r.ReadUInt32(); $n=$r.ReadUInt64(); for($j=0;$j -lt $n;$j++){ $null=Read-Val $at }; "array[$n]" }
  10 { $r.ReadUInt64() } 11 { $r.ReadInt64() } 12 { $r.ReadDouble() }
  default { throw "Unknown type $t" }
 }
}
try {
 $magic=$r.ReadUInt32(); if($magic -ne 0x46554747){throw 'Not GGUF'}
 $version=$r.ReadUInt32(); $tensors=$r.ReadUInt64(); $count=$r.ReadUInt64()
 "GGUF v$version tensors=$tensors metadata=$count"
 for($i=0;$i -lt $count;$i++){ $key=Read-Str; $type=$r.ReadUInt32(); $value=Read-Val $type; if($key -notmatch 'tokenizer'){ "$key = $value" } }
} finally { $r.Dispose() }
