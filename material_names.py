"""Portable display names and stable identities across user-requested renames."""
import hashlib
import json
import os
import re
import uuid
from pathlib import Path


def read_metadata(path):
    try:
        if path.is_symlink() or path.stat().st_size>65536:return {}
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('format')!='surface-studio-name':return {}
        if not isinstance(data.get('name'),str) or not isinstance(data.get('libraryKey'),str):return {}
        if not re.fullmatch('[a-f0-9]{16}',data.get('id','')):return {}
        return data
    except (OSError,ValueError,TypeError):return {}


def apply_metadata(asset, path):
    data=read_metadata(path)
    if not data:return asset
    key=data['libraryKey']
    ident=hashlib.sha1((os.path.normcase(str(Path(asset['sourceRoot']).resolve()))+'|'+key).encode()).hexdigest()[:16] if asset.get('sourceRoot') else data['id']
    return {**asset,'name':data['name'],'id':ident,'libraryKey':key,'category':asset['category'] if asset.get('sourceRoot') else data.get('category',asset['category'])}


def rename_material(app, ident, name):
    if app.SCANNING:raise ValueError('正在扫描，请稍后重命名')
    asset=app.ASSETS.get(ident)
    if not asset:raise ValueError('材质不存在，请刷新')
    if not isinstance(name,str):raise ValueError('请输入材质名称')
    name=name.strip()
    if not name or len(name)>100 or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name in ('.','..') or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',name,re.I):
        raise ValueError('名称不能超过100字，或包含文件夹不允许的字符及保留名称')
    root=Path(asset.get('sourceRoot') or app.INDEX['root']).resolve()
    folder=root/asset['folder']
    if folder.is_symlink() or folder.is_junction() or not folder.resolve().is_relative_to(root):raise ValueError('材质路径无效')
    single=asset.get('kind')=='normal'
    source=folder/asset['preview'] if single else folder
    if source.is_symlink() or source.is_junction() or not source.exists():raise ValueError('材质已移动或路径无效')
    if not single and source.resolve()==root:raise ValueError('不能重命名材质库根目录，请先将该材质置于独立子文件夹')
    target=source.with_name(name+source.suffix if single else name)
    if target.exists() and not source.samefile(target):raise ValueError('已有同名文件或文件夹，请换一个名称')
    # Windows permits only a two-step rename for names differing in case.
    metadata=source.with_name(source.name+'.surface.json') if single else source/'.surface-studio.json'
    new_metadata=target.with_name(target.name+'.surface.json') if single else target/'.surface-studio.json'
    if single and new_metadata!=metadata and new_metadata.exists() and not (metadata.exists() and metadata.samefile(new_metadata)):raise ValueError('已有同名材质记录')
    if metadata.is_symlink():raise ValueError('材质记录路径无效')
    old=metadata.read_bytes() if metadata.exists() else None
    manifest=source/'surface-material.json' if asset.get('kind')=='blend' else None
    manifest_bytes=manifest.read_bytes() if manifest else None
    app.organizer.snapshot(app,'rename')
    info={'format':'surface-studio-name','name':name,'id':ident,'libraryKey':asset.get('libraryKey',asset['folder']),'category':asset['category']}
    temporary=source.with_name('.ss-rename-'+uuid.uuid4().hex)
    moved=False
    try:
        app.save_json(metadata,info)
        if manifest:
            data=json.loads(manifest_bytes);data['name']=name;app.save_json(manifest,data)
        if source.name!=target.name:
            source.rename(temporary)
            try:temporary.rename(target)
            except Exception:temporary.rename(source);raise
            moved=True
            if single:metadata.rename(new_metadata)
        app.scan()
        if app.SCAN_ERROR:raise ValueError(app.SCAN_ERROR)
        if ident not in app.ASSETS:raise ValueError('改名后未能识别材质，已撤销')
        return {'ok':True,'id':ident,'name':name,'path':str(target)}
    except Exception:
        if moved:
            target.rename(temporary);temporary.rename(source)
            if single and new_metadata.exists():new_metadata.rename(metadata)
        if old is None:metadata.unlink(missing_ok=True)
        else:metadata.write_bytes(old)
        if manifest:manifest.write_bytes(manifest_bytes)
        app.scan()
        raise
