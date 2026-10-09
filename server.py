"""Surface Studio — local, read-only material indexing and preview service."""
from __future__ import annotations
import hashlib, io, json, mimetypes, os, re, secrets, threading, time
from collections import Counter
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from PIL import Image, ImageOps
from blender_bridge import BlenderBridge

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('SURFACE_STUDIO_DATA', str(BASE / 'data')))
DATA.mkdir(exist_ok=True)
CACHE = DATA / 'thumbnails'
CACHE.mkdir(exist_ok=True)
DEFAULT_ROOT = str(DATA.parent / 'materials')
if not (DATA / 'config.json').exists():
    Path(DEFAULT_ROOT).mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get('SURFACE_STUDIO_PORT', '47831'))
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
THUMB_LOCK = threading.Semaphore(4)
CATEGORIES = {'Concrete':'混凝土','Soil':'土壤','Grass':'草地','Rock':'岩石','Fabric':'织物','Imperfections':'瑕疵纹理','Ground':'地表','Floors':'地板','Asphalt':'沥青','Sand':'沙地','Debris':'碎屑','Creature':'生物','Construction':'建筑','Metal':'金属','Paper':'纸张','Wood':'木材','Road':'道路','Brick':'砖墙','Wall':'墙面','Tree':'树皮','Misc':'杂项','Plaster':'灰泥','Moss':'苔藓','Stone':'石材','Other':'其他','Climber':'藤蔓','Plants':'植物','Edible':'食物','Leaf':'叶片'}
WORDS = {'rough':'粗糙','smooth':'光滑','coarse':'粗粒','fine':'细腻','cracked':'开裂','cracks':'裂纹','damaged':'破损','old':'老旧','painted':'涂漆','dirty':'脏污','clean':'干净','dry':'干燥','dried':'干燥','wet':'潮湿','mossy':'苔藓','moss':'苔藓','forest':'森林','gravel':'砾石','pebbles':'卵石','mud':'泥土','sandy':'沙质','snow':'雪','red':'红色','green':'绿色','blue':'蓝色','grey':'灰色','gray':'灰色','white':'白色','black':'黑色','brown':'棕色','yellow':'黄色','rusty':'锈蚀','rust':'铁锈','rusted':'锈蚀','brick':'砖','bricks':'砖','marble':'大理石','granite':'花岗岩','tiles':'瓷砖','tile':'瓷砖','wood':'木','wooden':'木质','planks':'木板','asphalt':'沥青','concrete':'混凝土','leather':'皮革','fabric':'织物','rock':'岩石','stone':'石材','sandstone':'砂岩','limestone':'石灰岩','ground':'地面','soil':'土壤','grass':'草地','metal':'金属','paper':'纸','bark':'树皮','floor':'地板','wall':'墙','road':'道路','cliff':'峭壁','beach':'海滩','leaves':'落叶','cobblestone':'鹅卵石','pavement':'路面','plaster':'灰泥','dirt':'泥土','debris':'碎屑','surface':'表面'}

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError): return default

def save_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)

CONFIG = read_json(DATA / 'config.json', {'root': DEFAULT_ROOT})
if not Path(CONFIG['root']).is_absolute():
    CONFIG['root'] = str((DATA.parent / CONFIG['root']).resolve())
STATE = read_json(DATA / 'state.json', {'favorites': [], 'collections': [], 'recent': []})
INDEX = {'assets': [], 'categories': [], 'root': CONFIG['root'], 'scannedAt': None, 'totalBytes': 0, 'warnings': []}
SCANNING = False
SCAN_ERROR = None
ASSETS = {}
BRIDGE = BlenderBridge(DATA / 'blender')

def scan():
    global INDEX, ASSETS, SCANNING, SCAN_ERROR
    with LOCK:
        if SCANNING: return
        SCANNING = True
        SCAN_ERROR = None
    try:
        root = Path(CONFIG['root'])
        if not root.is_dir(): raise ValueError('材质库路径不存在或无法读取')
        result, warnings = [], []
        for folder in sorted(root.iterdir()):
            if not folder.is_dir(): continue
            try:
                files = [f for f in folder.iterdir() if f.is_file()]
                meta_file = next((f for f in files if f.suffix.lower() == '.json'), None)
                meta = read_json(meta_file, {}) if meta_file else {}
                image_files = [f for f in files if f.suffix.lower() in ('.jpg','.jpeg','.png','.exr','.tif','.tiff')]
                if not image_files: continue
                preview = next((f for f in image_files if 'preview' in f.name.lower()), None)
                maps = []
                for f in image_files:
                    if f == preview: continue
                    channel = next((v for k,v in [('albedo','Albedo'),('basecolor','Albedo'),('diffuse','Albedo'),('normal','Normal'),('roughness','Roughness'),('displacement','Displacement'),('height','Displacement'),('metalness','Metalness'),('metallic','Metalness'),('_ao','AO'),('opacity','Opacity'),('specular','Specular'),('gloss','Gloss')] if k in f.name.lower()), 'Other')
                    maps.append({'name':f.name,'channel':channel,'bytes':f.stat().st_size,'ext':f.suffix[1:].upper()})
                preview = preview or next((f for f in image_files if 'albedo' in f.name.lower()), image_files[0])
                cat = folder.name.split('_')[0] or 'Other'
                if cat not in CATEGORIES: cat = 'Other'
                display = str(meta.get('name') or re.sub(r'_[^_]+_\d+K_.*$', '', folder.name).replace('_',' ')).strip().title()
                tags = [str(t) for t in meta.get('tags',[]) if isinstance(t,(str,int))]
                cats = [str(c) for c in meta.get('categories',[]) if isinstance(c,str)]
                translated = ' '.join(WORDS.get(w,w) for w in re.findall(r'[a-z]+', ' '.join([display,folder.name]+tags+cats).lower()))
                resolution = re.search(r'(?:^|_)(\d+)K(?:_|$)',folder.name,re.I)
                ident = hashlib.sha1(folder.name.encode()).hexdigest()[:16]
                details = {m['key']:m.get('value') for m in meta.get('meta',[]) if isinstance(m,dict) and 'key' in m}
                item = {'id':ident,'name':display,'folder':folder.name,'assetId':str(meta.get('id') or (meta_file.stem if meta_file else ident)),'category':cat,'categoryZh':CATEGORIES[cat],'tags':tags,'categories':cats,'search':translated,'resolution':(resolution.group(1)+'K') if resolution else '—','preview':preview.name,'maps':maps,'bytes':sum(f.stat().st_size for f in files),'modified':folder.stat().st_mtime,'meta':details}
                result.append(item)
            except (OSError,ValueError,TypeError) as exc: warnings.append(f'{folder.name}: {exc}')
        counts = Counter(a['category'] for a in result)
        new_index = {'assets':result,'categories':[{'id':k,'name':CATEGORIES[k],'count':v} for k,v in counts.most_common()],'root':str(root),'scannedAt':time.time(),'totalBytes':sum(a['bytes'] for a in result),'warnings':warnings}
        with LOCK:
            INDEX = new_index
            ASSETS = {a['id']:a for a in result}
            save_json(DATA / 'index.json',INDEX)
    except Exception as exc:
        SCAN_ERROR = str(exc)
    finally: SCANNING = False

def asset_file(ident, name):
    a = ASSETS.get(ident)
    if not a: raise ValueError('材质不存在')
    allowed = {a['preview']} | {m['name'] for m in a['maps']}
    if name not in allowed: raise ValueError('文件不存在')
    root = Path(INDEX['root']).resolve()
    path = (root / a['folder'] / name).resolve()
    if not path.is_relative_to(root): raise ValueError('无效路径')
    return path

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send(self, body, mime='application/json; charset=utf-8', status=200, cache=False):
        if isinstance(body, (dict,list)): body=json.dumps(body,ensure_ascii=False).encode('utf-8')
        if isinstance(body,str): body=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','public, max-age=86400' if cache else 'no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): pass

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == '/api/health': return self.send({'app':'Surface Studio','ready':True})
            if url.path == '/api/library':
                return self.send({**INDEX,'state':STATE,'token':TOKEN,'scanning':SCANNING,'error':SCAN_ERROR})
            if url.path == '/api/status': return self.send({'scanning':SCANNING,'error':SCAN_ERROR,'count':len(ASSETS)})
            if url.path == '/api/state': return self.send(STATE)
            if url.path == '/api/blender/status':
                return self.send({'sessions': BRIDGE.sessions(), 'protocol': 1})
            if url.path == '/api/blender/result':
                return self.send(BRIDGE.result(q.get('id', [''])[0]))
            if url.path == '/api/image':
                path = asset_file(q.get('id',[''])[0], q.get('file',[''])[0])
                size = min(2048,max(64,int(q.get('size',['480'])[0])))
                key = hashlib.sha1(f'v2|{path}|{path.stat().st_mtime_ns}|{size}'.encode()).hexdigest()
                cached = CACHE / (key+'.webp')
                if not cached.exists():
                    with THUMB_LOCK:
                        if not cached.exists():
                            with Image.open(path) as raw:
                                im = ImageOps.exif_transpose(raw)
                                im.thumbnail((size,size),Image.Resampling.LANCZOS)
                                if im.mode not in ('RGB','RGBA'): im=im.convert('RGBA')
                                buf=io.BytesIO(); im.save(buf,'WEBP',quality=88,method=4)
                                temp=cached.with_suffix('.'+secrets.token_hex(6)+'.tmp'); temp.write_bytes(buf.getvalue()); temp.replace(cached)
                return self.send(cached.read_bytes(),'image/webp',cache=True)
            if url.path == '/api/file':
                path=asset_file(q.get('id',[''])[0],q.get('file',[''])[0])
                return self.send(path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream',cache=True)
            static = '/index.html' if url.path == '/' else unquote(url.path)
            public = BASE / 'public'
            path = (public / static.lstrip('/')).resolve()
            if not path.is_relative_to(public.resolve()) or not path.is_file(): return self.send({'error':'未找到页面'},status=404)
            return self.send(path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        except (OSError,ValueError) as exc: return self.send({'error':str(exc)},status=400)

    def do_POST(self):
        if self.headers.get('X-Studio-Token') != TOKEN: return self.send({'error':'会话已过期，请刷新'},status=403)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return self.send({'error':'无效来源'},status=403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>1024*1024: raise ValueError('请求过大')
            body=json.loads(self.rfile.read(length) or '{}')
            endpoint=urlparse(self.path).path
            with LOCK:
                if endpoint == '/api/blender/apply':
                    a = ASSETS.get(body.get('asset'))
                    if not a: raise ValueError('材质不存在，请刷新素材库')
                    maps = []
                    for m in a['maps']:
                        path = asset_file(a['id'], m['name'])
                        if not path.is_file(): raise ValueError('贴图已移动或丢失，请重新扫描素材库')
                        maps.append({**m, 'path': str(path)})
                    manifest = {'id': a['id'], 'name': a['name'], 'assetId': a['assetId'],
                                'root': INDEX['root'], 'folder': a['folder'], 'maps': maps}
                    return self.send(BRIDGE.enqueue(body.get('session'), manifest,
                                     body.get('options', {}), body.get('revision')))
                if endpoint == '/api/state':
                    for key in ('favorites','collections','recent'):
                        if key in body:
                            if not isinstance(body[key],list): raise ValueError('无效数据')
                            STATE[key]=body[key]
                    save_json(DATA / 'state.json',STATE)
                    return self.send(STATE)
                if endpoint == '/api/open':
                    a=ASSETS.get(body.get('id'))
                    if not a: raise ValueError('材质不存在')
                    path = Path(INDEX['root']) / a['folder']
                    os.startfile(str(path))
                    return self.send({'ok':True})
                if endpoint == '/api/rescan':
                    if SCANNING: raise ValueError('正在扫描，请稍候')
                    root=body.get('root',CONFIG['root'])
                    if not isinstance(root,str) or not Path(root).is_dir(): raise ValueError('路径不存在，请输入完整的材质库文件夹路径')
                    CONFIG['root']=str(Path(root).resolve())
                    save_json(DATA / 'config.json',CONFIG)
                    threading.Thread(target=scan,daemon=True).start()
                    return self.send({'ok':True})
            return self.send({'error':'未知操作'},status=404)
        except (ValueError,OSError,TypeError) as exc: return self.send({'error':str(exc)},status=400)

if __name__ == '__main__':
    saved=read_json(DATA / 'index.json',None)
    if saved and saved.get('root')==CONFIG['root']:
        INDEX=saved; ASSETS={a['id']:a for a in INDEX['assets']}
    else: scan()
    print(f'Surface Studio http://127.0.0.1:{PORT} | {len(ASSETS)} materials',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
