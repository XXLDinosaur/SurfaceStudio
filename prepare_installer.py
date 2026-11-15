"""Create a clean, explicit installer payload; no personal data is copied."""
from pathlib import Path
import argparse
import shutil
import zipfile
from installer_sketchup import MEMBERS
from package_addon import package

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--app', type=Path, default=root/'dist/Surface Studio.exe')
parser.add_argument('--payload', type=Path, default=root/'dist/installer_payload')
args = parser.parse_args()
payload = args.payload
payload.mkdir(parents=True, exist_ok=True)
if not args.app.is_file():
    raise RuntimeError('先运行 build.ps1 构建 Surface Studio.exe')
shutil.copy2(args.app, payload/'Surface Studio.exe')
package(payload/'surface_studio_bridge.zip')
shutil.copy2(root/'INSTALLER.md', payload/'安装与使用说明.txt')
shutil.copy2(root/'LICENSE', payload/'LICENSE')
with zipfile.ZipFile(payload/'SurfaceStudio-SketchUp.rbz','w',zipfile.ZIP_DEFLATED) as archive:
    for name in MEMBERS:
        archive.write(root/'sketchup_addon'/name,name)
allowed = {'SurfaceStudio-SketchUp.rbz', 'Surface Studio.exe', 'surface_studio_bridge.zip', '安装与使用说明.txt', 'LICENSE'}
assert {p.name for p in payload.iterdir()} == allowed, 'Payload contains unexpected files'
print('Prepared clean installer payload')
