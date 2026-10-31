# Downloads official dependencies; never accesses a phone or installs a driver.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$spec = Get-Content -LiteralPath '.\downloads.json' -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path '.\downloads', '.\vendor', '.\drivers' | Out-Null
function Get-CheckedFile($item, $target) {
    if (-not (Test-Path -LiteralPath $target)) { Invoke-WebRequest -Uri $item.url -OutFile $target }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
        throw "SHA256 mismatch: $target. Stop; do not bypass the check."
    }
}
if (-not (Test-Path -LiteralPath '.\vendor\mtkclient')) {
    Get-CheckedFile $spec.mtkclient '.\downloads\mtkclient-v2.1.4.1.zip'
    Expand-Archive -LiteralPath '.\downloads\mtkclient-v2.1.4.1.zip' -DestinationPath '.\vendor'
    Rename-Item -LiteralPath '.\vendor\mtkclient-2.1.4.1' -NewName 'mtkclient'
}
if (-not (Test-Path -LiteralPath '.\platform-tools')) {
    Get-CheckedFile $spec.platform_tools '.\downloads\platform-tools.zip'
    Expand-Archive -LiteralPath '.\downloads\platform-tools.zip' -DestinationPath '.'
}
Get-CheckedFile $spec.usbdk '.\drivers\UsbDk_1.0.22_x64.msi'
Get-CheckedFile $spec.fastboot_driver '.\drivers\mediatek-201c.cab'
if (-not (Test-Path -LiteralPath '.\drivers\fastboot')) {
    New-Item -ItemType Directory -Path '.\drivers\fastboot' | Out-Null
    & expand.exe '-F:*' '.\drivers\mediatek-201c.cab' '.\drivers\fastboot'
    if ($LASTEXITCODE -ne 0) { throw 'Driver CAB extraction failed' }
}
if (-not (Test-Path -LiteralPath '.\runtime\python.exe')) {
    if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python x64 3.10-3.13 is required' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements-cli.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
}
Write-Output 'Done. No phone accessed and no driver installed. Read README.md next.'
