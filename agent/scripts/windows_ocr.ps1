param([string]$InputImage, [string]$LanguageTag='fr-FR', [switch]$Status)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime] | Out-Null
if($Status) {
    @{languages=@([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object {$_.LanguageTag});
      windows_build=[Environment]::OSVersion.Version.ToString();
      engine_version=(Get-Item -LiteralPath "$env:SystemRoot\System32\Windows.Media.Ocr.dll").VersionInfo.FileVersion;
      maximum_dimension=[Windows.Media.Ocr.OcrEngine]::MaxImageDimension} | ConvertTo-Json -Compress
    exit 0
}
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
$taskMethod=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
function Await-Result($operation,[type]$resultType) {
    $task=$taskMethod.MakeGenericMethod($resultType).Invoke($null,@($operation))
    $task.GetAwaiter().GetResult()
}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($LanguageTag))
if($null -eq $engine){throw 'Langue OCR indisponible sur Windows'}
$file=Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($InputImage)) ([Windows.Storage.StorageFile])
$stream=Await-Result ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
try {
    $decoder=Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap=Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    try {
        $result=Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $lines=@($result.Lines | ForEach-Object {
            @{text=$_.Text;words=@($_.Words | ForEach-Object {
                @{text=$_.Text;rectangle=@{x=$_.BoundingRect.X;y=$_.BoundingRect.Y;width=$_.BoundingRect.Width;height=$_.BoundingRect.Height}}
            })}
        })
        @{text=($lines.text -join "`n");language=$engine.RecognizerLanguage.LanguageTag;
          width=$bitmap.PixelWidth;height=$bitmap.PixelHeight;lines=$lines} | ConvertTo-Json -Depth 8 -Compress
    } finally {$bitmap.Dispose()}
} finally {$stream.Dispose()}
