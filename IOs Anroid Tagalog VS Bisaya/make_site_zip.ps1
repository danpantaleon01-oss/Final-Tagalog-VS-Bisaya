# Build Tagalog-VS-Bisaya-website.zip with FORWARD-SLASH entry names.
# (PowerShell 5.1's Compress-Archive writes entries like "assets\icon.png",
# and Netlify's unzipper does not nest those — the subfolders fall off the
# site. This script bypasses Compress-Archive and names every entry itself.)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$site = Join-Path $PSScriptRoot "site"
if (-not (Test-Path $site)) { Write-Error "site folder not found next to this script"; exit 1 }

$zip = Join-Path $PSScriptRoot "Tagalog-VS-Bisaya-website.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

$fs = [System.IO.File]::Open($zip, [System.IO.FileMode]::Create)
$za = New-Object System.IO.Compression.ZipArchive($fs, [System.IO.Compression.ZipArchiveMode]::Create)

$files = Get-ChildItem $site -Recurse -File
foreach ($f in $files) {
    $rel = $f.FullName.Substring($site.Length + 1).Replace('\', '/')
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($za, $f.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal)
}
$za.Dispose()
$fs.Dispose()

# Verify: every entry must use forward slashes only
$probe = [System.IO.Compression.ZipFile]::OpenRead($zip)
$bad = @($probe.Entries | Where-Object { $_.FullName -like '*\*' })
$probe.Dispose()
if ($bad.Count -gt 0) {
    Write-Error "Zip still contains backslash entries: $($bad | Select-Object -First 3 -ExpandProperty FullName)"
    exit 1
}
"OK  {0}  ({1:N1} MB, {2} entries, all forward-slash paths)" -f $zip, ((Get-Item $zip).Length / 1MB), $files.Count
