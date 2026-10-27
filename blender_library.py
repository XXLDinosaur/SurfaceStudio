from material_names import apply_metadata
"""Index portable Blender material packages without opening or executing .blend files."""
import hashlib
import json
import os
from pathlib import Path
import re

FORMAT = 'surface-studio-blender-material'


def scan_blender_materials(roots, warnings):
    result, visited = [], set()
    for source in roots:
        root = Path(source).resolve()
        if not root.is_dir():
            warnings.append('Blender 材质库路径不存在：' + str(root))
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_junction())
            folder = Path(directory).resolve()
            if not folder.is_relative_to(root) or folder in visited or 'surface-material.json' not in files:
                continue
            visited.add(folder)
            try:
                manifest = folder/'surface-material.json'
                if manifest.stat().st_size > 1024*1024:
                    raise ValueError('材质说明文件过大')
                meta = json.loads(manifest.read_text(encoding='utf-8'))
                if not isinstance(meta, dict) or meta.get('format') != FORMAT or meta.get('version') != 1:
                    raise ValueError('不支持的 Blender 材质包版本')
                uid = meta.get('id', '')
                if not isinstance(uid, str) or not re.fullmatch('[a-f0-9]{32}', uid):
                    raise ValueError('材质编号无效')
                for key, expected in [('blendFile', 'material.blend'), ('preview', 'preview.png')]:
                    if meta.get(key) != expected or not (folder/expected).is_file() or not (folder/expected).resolve().is_relative_to(folder):
                        raise ValueError('材质包缺少 ' + expected)
                version = meta.get('blenderVersion')
                if not isinstance(version, list) or len(version) != 3 or not all(type(v) is int and v >= 0 for v in version):
                    raise ValueError('Blender 版本无效')
                if not isinstance(meta.get('materialName'), str) or not meta['materialName'].strip():
                    raise ValueError('缺少材质数据名称')
                relative = folder.relative_to(root).as_posix()
                key = 'blend:' + relative + ':' + uid
                ident = hashlib.sha1((os.path.normcase(str(root))+'|'+key).encode()).hexdigest()[:16]
                stat = (folder/'material.blend').stat()
                result.append({'id':ident, 'assetId':uid, 'name':str(meta.get('name') or meta['materialName']),
                    'folder':relative, 'sourceRoot':str(root), 'libraryKey':key, 'kind':'blend',
                    'category':'Uncategorized', 'categoryZh':'未分类', 'tags':['Blender','节点材质'],
                    'categories':['Uncategorized'], 'search':str(meta.get('name',''))+' blender 节点 自制 材质',
                    'resolution':'BLEND', 'preview':'preview.png', 'maps':[],
                    'bytes':stat.st_size+(folder/'preview.png').stat().st_size+manifest.stat().st_size,
                    'modified':stat.st_mtime, 'meta':{}, 'blendFile':'material.blend',
                    'materialName':meta['materialName'], 'blenderVersion':version,
                    'previewWarning':str(meta.get('previewWarning',''))})
            except (OSError, ValueError, TypeError) as exc:
                warnings.append(str(folder)+': '+str(exc))
    return [apply_metadata(a,Path(a['sourceRoot'])/a['folder']/'.surface-studio.json') for a in result]
