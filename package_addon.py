from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
source=root/'blender_addon'/'surface_studio_bridge'
with zipfile.ZipFile(root/'surface_studio_bridge.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for file in source.rglob('*'):
        if file.is_file() and file.suffix in ('.py','.md'):
            archive.write(file,file.relative_to(source.parent))
print('Packaged surface_studio_bridge.zip')
