param([string]$Python = 'python', [string]$OutputDirectory = 'dist', [string]$ApplicationPath = 'dist\Surface Studio.exe')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$payloadPath = Join-Path (Join-Path $PSScriptRoot $OutputDirectory) 'installer_payload'
& $Python prepare_installer.py --app $ApplicationPath --payload $payloadPath
if ($LASTEXITCODE -ne 0) { throw 'Installer payload failed' }
$uiPath = Join-Path $PSScriptRoot 'installer_ui.html'
$workerPath = Join-Path $PSScriptRoot 'installer_blender.py'
$iconPath = Join-Path $PSScriptRoot 'surface.ico'
& $Python -m PyInstaller --noconfirm --onefile --windowed --name 'SurfaceStudio-Setup' --icon $iconPath --add-data "$uiPath;." --add-data "$workerPath;." --add-data "$payloadPath;installer_payload" --distpath $OutputDirectory --workpath build --specpath build --collect-all webview --hidden-import clr_loader --exclude-module numpy --exclude-module matplotlib --exclude-module tkinter --exclude-module IPython --exclude-module scipy --exclude-module pandas installer.py
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
