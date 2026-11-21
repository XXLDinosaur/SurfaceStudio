param([string]$Python = 'python', [string]$OutputDirectory = 'dist')
$ErrorActionPreference = 'Stop'
$pythonRuntime = $Python
$assetsPath = Join-Path $PSScriptRoot 'public'
$iconPath = Join-Path $PSScriptRoot 'surface.ico'
$sslSupport = (& $pythonRuntime -c "import ssl; from pathlib import Path; print(Path(ssl.__file__).with_name('codex-rejected-cas.pem'))").Trim()
$sslData = @()
if (Test-Path -LiteralPath $sslSupport) { $sslData = @('--add-data', "$sslSupport;.") }
Set-Location $PSScriptRoot
& $pythonRuntime -m PyInstaller --noconfirm --onefile --windowed --name 'Surface Studio' --icon $iconPath --add-data "$assetsPath;public" @sslData --distpath $OutputDirectory --workpath build --specpath build --collect-all webview --hidden-import clr_loader --collect-all OpenImageIO --exclude-module matplotlib --exclude-module tkinter --exclude-module IPython --exclude-module scipy --exclude-module pandas desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
