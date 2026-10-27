param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$AppDir=Join-Path $env:LOCALAPPDATA 'OmniForge\App'
$Api='https://api.github.com/repos/R347H4CK3R/OmniForge/releases?per_page=30'
$Headers=@{'User-Agent'='OmniForge-Windows-Updater';'Accept'='application/vnd.github+json'}
$Releases=Invoke-RestMethod -Uri $Api -Headers $Headers -TimeoutSec 30
$Release=$Releases | Where-Object { $_.tag_name -match '^win-\d+$' -and -not $_.draft -and -not $_.prerelease } | Sort-Object {[int]($_.tag_name -replace '^win-','')} -Descending | Select-Object -First 1
if (-not $Release) { throw 'No published Windows release found.' }
$Version=$Release.tag_name
$CurrentFile=Join-Path $AppDir 'installed-version.txt'
$Current=if(Test-Path $CurrentFile){(Get-Content $CurrentFile -Raw).Trim()}else{''}
if ($Version -eq $Current){Write-Host "OmniForge is current: $Version";exit 0}
Write-Host "Available update: $Version (installed: $Current)"
if ($CheckOnly){exit 0}
$ZipAsset=$Release.assets|Where-Object name -eq 'OmniForge-Windows.zip'|Select-Object -First 1
$HashAsset=$Release.assets|Where-Object name -eq 'OmniForge-Windows.zip.sha256'|Select-Object -First 1
if (-not $ZipAsset -or -not $HashAsset){throw 'Release missing archive or checksum'}
$Temp=Join-Path $env:TEMP ('OmniForgeUpdate-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $Temp|Out-Null
try{
  $Zip=Join-Path $Temp 'OmniForge-Windows.zip'
  $HashPath=Join-Path $Temp 'OmniForge-Windows.zip.sha256'
  Invoke-WebRequest $ZipAsset.browser_download_url -OutFile $Zip -TimeoutSec 180
  Invoke-WebRequest $HashAsset.browser_download_url -OutFile $HashPath -TimeoutSec 30
  $Expected=((Get-Content $HashPath -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
  $Actual=(Get-FileHash $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($Actual -ne $Expected){throw 'Checksum mismatch; update aborted'}
  $Stage=Join-Path $Temp 'package'
  Expand-Archive $Zip -DestinationPath $Stage
  foreach($file in @('OmniForgeHost.exe','OmniForgeWorker.exe','Start-OmniForge.ps1')) {
    if(-not(Test-Path (Join-Path $Stage $file))){throw "Missing $file"}
  }
  New-Item -ItemType Directory -Force $AppDir|Out-Null
  # Never overwrite binaries while they are running.
  $active=Get-Process OmniForgeHost,OmniForgeWorker -ErrorAction SilentlyContinue
  if($active){throw 'Close OmniForge Host and Worker before applying this update.'}
  Get-ChildItem $Stage -File | ForEach-Object {Copy-Item $_.FullName (Join-Path $AppDir $_.Name) -Force}
  Set-Content $CurrentFile $Version
  Write-Host "Installed $Version to $AppDir. Start with: $AppDir\Start-OmniForge.ps1"
} finally {Remove-Item $Temp -Recurse -Force -ErrorAction SilentlyContinue}
