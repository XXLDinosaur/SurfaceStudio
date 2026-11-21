param([string]$Python = 'python', [string]$OutputDirectory = 'dist', [string]$ApplicationPath = 'dist\Surface Studio.exe')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$payloadPath = Join-Path (Join-Path $PSScriptRoot $OutputDirectory) 'installer_payload'
& $Python prepare_installer.py --app $ApplicationPath --payload $payloadPath
if ($LASTEXITCODE -ne 0) { throw 'Installer payload failed' }
$uiPath = Join-Path $PSScriptRoot 'installer_ui.html'
$workerPath = Join-Path $PSScriptRoot 'installer_blender.py'
$iconPath = Join-Path $PSScriptRoot 'surface.ico'
$sslSupport = (& $Python -c "import ssl; from pathlib import Path; print(Path(ssl.__file__).with_name('codex-rejected-cas.pem'))").Trim()
$sslData = @()
if (Test-Path -LiteralPath $sslSupport) { $sslData = @('--add-data', "$sslSupport;.") }
& $Python -m PyInstaller --noconfirm --onefile --windowed --name 'SurfaceStudio-Setup' --icon $iconPath --add-data "$uiPath;." --add-data "$workerPath;." --add-data "$payloadPath;installer_payload" @sslData --distpath $OutputDirectory --workpath build --specpath build --collect-all webview --hidden-import clr_loader --exclude-module numpy --exclude-module matplotlib --exclude-module tkinter --exclude-module IPython --exclude-module scipy --exclude-module pandas installer.py
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
