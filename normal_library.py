from material_names import apply_metadata
"""Explicit normal-map source: each image is an independent, stable asset."""
import hashlib
import os
import re
from pathlib import Path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.exr', '.tif', '.tiff'}


def scan_normals(source, warnings):
    root = Path(source).resolve()
    if not root.is_dir():
        warnings.append('法线贴图库路径不存在：'+str(root))
        return []
    result = []
    def error(exc): warnings.append('法线贴图库：'+str(exc))
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=error):
        dirs[:] = sorted(d for d in dirs if not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_junction() and (Path(directory)/d).resolve().is_relative_to(root))
        for name in sorted(names):
            path = Path(directory)/name
            if path.suffix.lower() not in IMAGE_EXTENSIONS: continue
            try:
                if not path.resolve().is_relative_to(root) or not path.is_file(): continue
                relative = path.relative_to(root)
                key = 'normal:'+relative.as_posix()
                ident = hashlib.sha1((os.path.normcase(str(root))+'|'+key).encode('utf-8')).hexdigest()[:16]
                stat = path.stat()
                resolution = re.search(r'(?:^|[_ .-])(\d+)K(?:[_ .-]|$)',name,re.I)
                result.append({'id':ident,'name':path.stem,'folder':relative.parent.as_posix(),
                    'sourceRoot':str(root),'libraryKey':key,'kind':'normal','normalOnly':True,
                    'assetId':ident,'category':'NormalOnly','categoryZh':'法线贴图','tags':['法线','Normal'],
                    'categories':['NormalOnly'],'search':relative.as_posix().lower()+' 法线 水波 normal water',
                    'resolution':resolution.group(1).upper()+'K' if resolution else '—','preview':name,
                    'maps':[{'name':name,'channel':'Normal','bytes':stat.st_size,'ext':path.suffix[1:].upper()}],
                    'bytes':stat.st_size,'modified':stat.st_mtime,'meta':{}})
            except OSError as exc: warnings.append('法线 '+str(path)+': '+str(exc))
    return [apply_metadata(a,Path(a['sourceRoot'])/a['folder']/(a['preview']+'.surface.json')) for a in result]
