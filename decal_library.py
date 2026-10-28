"""Read-only indexing of explicit decal libraries, one folder per decal."""
import hashlib,json,re,os
from pathlib import Path
from material_names import apply_metadata

def scan_decals(directory,warnings):
    if not directory:return []
    root=Path(directory).resolve();result=[]
    if not root.is_dir():warnings.append('贴花库无法读取：'+str(root));return []
    channels=[('albedo','Albedo'),('basecolor','Albedo'),('diffuse','Albedo'),('opacity','Opacity'),('mask','Opacity'),('normal','Normal'),('roughness','Roughness'),('metalness','Metalness'),('_ao','AO')]
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith('.') or folder.is_symlink() or folder.is_junction() or not folder.resolve().is_relative_to(root):continue
        try:
            files=[f for f in folder.iterdir() if f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(root)]
            maps=[];preview=None
            for f in files:
                if f.suffix.lower() not in ('.jpg','.jpeg','.png','.tif','.tiff','.exr'):continue
                if 'preview' in f.name.lower():preview=f;continue
                channel=next((v for k,v in channels if k in f.name.lower()),None)
                if channel:maps.append({'name':f.name,'channel':channel,'bytes':f.stat().st_size,'ext':f.suffix[1:].upper()})
            color=next((m for m in maps if m['channel']=='Albedo'),None)
            if not color or not any(m['channel']=='Opacity' for m in maps):
                warnings.append(folder.name+'：贴花需要 Albedo 和 Opacity/Mask，已跳过');continue
            metadata=next((f for f in files if f.suffix.lower()=='.json' and not f.name.startswith('.')),None)
            try:meta=json.loads(metadata.read_text(encoding='utf-8-sig')) if metadata else {}
            except (ValueError,OSError):meta={}
            if not isinstance(meta,dict):meta={}
            key='decal:'+folder.name
            ident=hashlib.sha1((os.path.normcase(str(root))+'|'+key).encode()).hexdigest()[:16]
            res=re.search(r'(\d+)K',folder.name+' '+color['name'],re.I)
            result.append({'id':ident,'kind':'decal','name':str(meta.get('name') or folder.name),'folder':folder.name,'sourceRoot':str(root),'assetId':str(meta.get('id') or ident),'category':'Decal','categoryZh':'贴花','tags':['贴花','污渍','decal'],'categories':['Decal'],'search':folder.name,'resolution':res.group(1)+'K' if res else '—','preview':preview.name if preview else color['name'],'maps':maps,'bytes':sum(f.stat().st_size for f in files),'modified':folder.stat().st_mtime,'meta':{}})
        except (OSError,ValueError,TypeError) as exc:warnings.append(folder.name+': '+str(exc))
    return [apply_metadata({**asset,'libraryKey':'decal:'+asset['folder']},root/asset['folder']/'.surface-studio.json') for asset in result]
