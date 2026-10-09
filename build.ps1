param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$pythonRuntime = $Python
$assetsPath = Join-Path $PSScriptRoot 'public'
$iconPath = Join-Path $PSScriptRoot 'surface.ico'
Set-Location $PSScriptRoot
& $pythonRuntime -m PyInstaller --noconfirm --onefile --windowed --name 'Surface Studio' --icon $iconPath --add-data "$assetsPath;public" --distpath dist --workpath build --specpath build --collect-all webview --hidden-import clr_loader --exclude-module numpy --exclude-module matplotlib --exclude-module tkinter --exclude-module IPython --exclude-module scipy --exclude-module pandas desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
