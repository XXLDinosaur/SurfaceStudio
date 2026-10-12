param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& $Python prepare_installer.py
if ($LASTEXITCODE -ne 0) { throw 'Installer payload failed' }
$uiPath = Join-Path $PSScriptRoot 'installer_ui.html'
$workerPath = Join-Path $PSScriptRoot 'installer_blender.py'
$payloadPath = Join-Path $PSScriptRoot 'dist/installer_payload'
$iconPath = Join-Path $PSScriptRoot 'surface.ico'
& $Python -m PyInstaller --noconfirm --onefile --windowed --name 'SurfaceStudio-Setup' --icon $iconPath --add-data "$uiPath;." --add-data "$workerPath;." --add-data "$payloadPath;installer_payload" --distpath dist --workpath build --specpath build --collect-all webview --hidden-import clr_loader --exclude-module numpy --exclude-module matplotlib --exclude-module tkinter --exclude-module IPython --exclude-module scipy --exclude-module pandas installer.py
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
