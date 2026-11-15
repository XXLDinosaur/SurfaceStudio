from pathlib import Path
import zipfile
import sys

root=Path(__file__).resolve().parent
source=root/'blender_addon'/'surface_studio_bridge'

def package(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in source.rglob('*'):
            if file.is_file() and file.suffix in ('.py','.md'):
                archive.write(file,file.relative_to(source.parent))
    print('Packaged ' + str(output))

if __name__ == '__main__':
    package(sys.argv[1] if len(sys.argv) > 1 else root/'surface_studio_bridge.zip')
