param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'Surface Studio.exe'
if (Test-Path -LiteralPath $exe) {
    Start-Process -FilePath $exe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} else {
    Set-Location $PSScriptRoot
    & $Python (Join-Path $PSScriptRoot 'desktop.py')
    if ($LASTEXITCODE -ne 0) { throw 'Surface Studio failed to start' }
}
