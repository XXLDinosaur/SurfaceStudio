"""Create a clean, explicit installer payload; no personal data is copied."""
from pathlib import Path
import runpy
import shutil

root = Path(__file__).resolve().parent
runpy.run_path(str(root/'package_addon.py'), run_name='__main__')
payload = root/'dist/installer_payload'
payload.mkdir(parents=True, exist_ok=True)
if not (root/'dist/Surface Studio.exe').is_file():
    raise RuntimeError('先运行 build.ps1 构建 Surface Studio.exe')
shutil.copy2(root/'dist/Surface Studio.exe', payload/'Surface Studio.exe')
shutil.copy2(root/'surface_studio_bridge.zip', payload/'surface_studio_bridge.zip')
shutil.copy2(root/'INSTALLER.md', payload/'安装与使用说明.txt')
allowed = {'Surface Studio.exe', 'surface_studio_bridge.zip', '安装与使用说明.txt'}
assert {p.name for p in payload.iterdir()} == allowed, 'Payload contains unexpected files'
print('Prepared clean installer payload')
