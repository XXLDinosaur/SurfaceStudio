"""Surface Studio — local, read-only material indexing and preview service."""
from __future__ import annotations
import hashlib, io, json, mimetypes, os, re, secrets, threading, time, unicodedata
from collections import Counter
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from PIL import Image, ImageOps
from blender_bridge import BlenderBridge
import organizer
import material_names
import asset_categories
from release_notes import NOTES
from normal_library import scan_normals
from decal_library import scan_decals
from blender_library import scan_blender_materials
from app_context import ApplicationContext, expose_legacy_state
import sys
APP = ApplicationContext()
BASE = Path(__file__).resolve().parent
APP.DATA = Path(os.environ.get('SURFACE_STUDIO_DATA', str(BASE / 'data')))
APP.DATA.mkdir(exist_ok=True)
APP.CACHE = APP.DATA / 'thumbnails'
APP.CACHE.mkdir(exist_ok=True)
APP.DEFAULT_ROOT = str(APP.DATA.parent / 'materials')
if not (APP.DATA / 'config.json').exists():
    Path(APP.DEFAULT_ROOT).mkdir(parents=True, exist_ok=True)
APP.PORT = int(os.environ.get('SURFACE_STUDIO_PORT', '47831'))
APP.TOKEN = secrets.token_urlsafe(32)
APP.LOCK = threading.RLock()
APP.THUMB_LOCK = threading.Semaphore(4)
CATEGORIES = {'Decal': '贴花', 'Concrete': '混凝土', 'Soil': '土壤', 'Grass': '草地', 'Rock': '岩石', 'Fabric': '织物', 'Imperfections': '瑕疵纹理', 'Ground': '地表', 'Floors': '地板', 'Asphalt': '沥青', 'Sand': '沙地', 'Debris': '碎屑', 'Creature': '生物', 'Construction': '建筑', 'Metal': '金属', 'Paper': '纸张', 'Wood': '木材', 'Road': '道路', 'Brick': '砖墙', 'Wall': '墙面', 'Tree': '树皮', 'Misc': '杂项', 'Plaster': '灰泥', 'Moss': '苔藓', 'Stone': '石材', 'Other': '其他', 'Climber': '藤蔓', 'Plants': '植物', 'Edible': '食物', 'Leaf': '叶片', 'NormalOnly': '法线贴图', 'Blender': 'Blender 材质', 'Uncategorized': '未分类'}
CATEGORIES.update(asset_categories.LABELS)
WORDS = {'rough': '粗糙', 'smooth': '光滑', 'coarse': '粗粒', 'fine': '细腻', 'cracked': '开裂', 'cracks': '裂纹', 'damaged': '破损', 'old': '老旧', 'painted': '涂漆', 'dirty': '脏污', 'clean': '干净', 'dry': '干燥', 'dried': '干燥', 'wet': '潮湿', 'mossy': '苔藓', 'moss': '苔藓', 'forest': '森林', 'gravel': '砾石', 'pebbles': '卵石', 'mud': '泥土', 'sandy': '沙质', 'snow': '雪', 'red': '红色', 'green': '绿色', 'blue': '蓝色', 'grey': '灰色', 'gray': '灰色', 'white': '白色', 'black': '黑色', 'brown': '棕色', 'yellow': '黄色', 'rusty': '锈蚀', 'rust': '铁锈', 'rusted': '锈蚀', 'brick': '砖', 'bricks': '砖', 'marble': '大理石', 'granite': '花岗岩', 'tiles': '瓷砖', 'tile': '瓷砖', 'wood': '木', 'wooden': '木质', 'planks': '木板', 'asphalt': '沥青', 'concrete': '混凝土', 'leather': '皮革', 'fabric': '织物', 'rock': '岩石', 'stone': '石材', 'sandstone': '砂岩', 'limestone': '石灰岩', 'ground': '地面', 'soil': '土壤', 'grass': '草地', 'metal': '金属', 'paper': '纸', 'bark': '树皮', 'floor': '地板', 'wall': '墙', 'road': '道路', 'cliff': '峭壁', 'beach': '海滩', 'leaves': '落叶', 'cobblestone': '鹅卵石', 'pavement': '路面', 'plaster': '灰泥', 'dirt': '泥土', 'debris': '碎屑', 'surface': '表面'}

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default

def save_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)
APP.CONFIG = read_json(APP.DATA / 'config.json', {'root': APP.DEFAULT_ROOT})
if not Path(APP.CONFIG['root']).is_absolute():
    APP.CONFIG['root'] = str((APP.DATA.parent / APP.CONFIG['root']).resolve())
APP.STATE = read_json(APP.DATA / 'state.json', {'favorites': [], 'collections': [], 'recent': []})
APP.INDEX = {'assets': [], 'categories': [], 'root': APP.CONFIG['root'], 'scannedAt': None, 'totalBytes': 0, 'warnings': []}
APP.SCANNING = False
APP.SCAN_ERROR = None
APP.ASSETS = {}
APP.BRIDGE = BlenderBridge(APP.DATA / 'blender')

def category_data():
    data = read_json(APP.DATA / 'categories.json', {})
    key = os.path.normcase(str(Path(APP.INDEX['root']).resolve()))
    return (data, key, data.get(key, {'custom': {}, 'assignments': {}}))

def categorized_library():
    _, _, edits = category_data()
    catalog = {**CATEGORIES, **asset_categories.LABELS, **edits['custom'], **edits.get('names', {})}
    items = []
    for source in APP.INDEX['assets']:
        automatic = asset_categories.automatic_category(source)
        category = edits['assignments'].get(source['id'], automatic)
        if category == 'Blender':
            category = 'Uncategorized'
        if category not in catalog:
            category = source['category']
        normal_only = bool(source.get('normalOnly') or (source['maps'] and all((m['channel'] == 'Normal' for m in source['maps']))))
        normal_preview = next((m['name'] for m in source['maps'] if m['channel'] == 'Normal' and m['ext'] != 'EXR'), next((m['name'] for m in source['maps'] if m['channel'] == 'Normal'), source['preview']))
        items.append({**source, 'preview': normal_preview if normal_only else source['preview'], 'category': category, 'categoryZh': catalog[category], 'normalOnly': normal_only, 'assetGroup': asset_categories.asset_group({**source, 'normalOnly': normal_only}), 'automaticCategory': automatic, 'manualCategory': source['id'] in edits['assignments']})
    counts = Counter((a['category'] for a in items))
    categories = [{'id': k, 'name': catalog[k], 'count': counts[k]} for k in dict.fromkeys([*counts, 'Uncategorized', *edits['custom']])]
    categories.sort(key=lambda c: (c['id'] != 'Uncategorized', -c['count']))
    return {**APP.INDEX, 'assets': items, 'categories': categories, 'materialSaveRoot': APP.CONFIG.get('materialSaveRoot', ''), 'effectiveMaterialSaveRoot': APP.CONFIG.get('materialSaveRoot') or APP.CONFIG['root'], 'categoryOptions': [{'id': k, 'name': v} for k, v in catalog.items() if k != 'Blender']}

def edit_category(body):
    data, key, edits = category_data()
    action = body.get('action')
    asset = body.get('asset')
    if asset is not None and (not isinstance(asset, str) or asset not in APP.ASSETS):
        raise ValueError('材质不存在，请刷新后重试')
    if action in ('create', 'rename'):
        name = body.get('name')
        if not isinstance(name, str):
            raise ValueError('请输入分类名称')
        name = unicodedata.normalize('NFKC', name).strip()
        if not name or len(name) > 40 or any((ord(c) < 32 for c in name)):
            raise ValueError('分类名称需要为 1–40 个有效字符')
        catalog = {**CATEGORIES, **edits['custom'], **edits.get('names', {})}
        target = body.get('category') if action == 'rename' else None
        if action == 'rename' and (not isinstance(target, str) or target not in catalog):
            raise ValueError('分类不存在')
        if name.casefold() in {unicodedata.normalize('NFKC', v).casefold() for k, label in catalog.items() if k != target for v in (k, label)}:
            raise ValueError('该分类已存在，请直接选择已有分类')
        if action == 'rename':
            edits.setdefault('names', {})[target] = name
        else:
            target = 'custom-' + secrets.token_hex(8)
            edits['custom'][target] = name
            if asset is not None:
                edits['assignments'][asset] = target
    elif action == 'assign':
        if asset is None:
            raise ValueError('请选择材质')
        target = body.get('category')
        if target is None:
            edits['assignments'].pop(asset, None)
        else:
            if not isinstance(target, str) or target not in {**CATEGORIES, **edits['custom']}:
                raise ValueError('分类不存在')
            edits['assignments'][asset] = target
    else:
        raise ValueError('无效的分类操作')
    data[key] = edits
    save_json(APP.DATA / 'categories.json', data)
    return {'ok': True}

def scan():
    with APP.LOCK:
        if APP.SCANNING:
            return
        APP.SCANNING = True
        APP.SCAN_ERROR = None
        configuration = json.loads(json.dumps(APP.CONFIG))
    try:
        root = Path(configuration['root'])
        if not root.is_dir():
            raise ValueError('材质库路径不存在或无法读取')
        result, warnings = ([], [])
        normal_root = configuration.get('normalRoot', '')
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or folder.name.startswith('.') or (folder / 'surface-material.json').exists():
                continue
            if configuration.get('decalRoot') and folder.resolve().is_relative_to(Path(configuration['decalRoot']).resolve()):
                continue
            if normal_root and folder.resolve().is_relative_to(Path(normal_root).resolve()):
                continue
            try:
                files = [f for f in folder.iterdir() if f.is_file()]
                meta_file = next((f for f in files if f.suffix.lower() == '.json' and (not f.name.startswith('.'))), None)
                meta = read_json(meta_file, {}) if meta_file else {}
                image_files = [f for f in files if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.exr', '.tif', '.tiff')]
                if not image_files:
                    continue
                preview = next((f for f in image_files if 'preview' in f.name.lower()), None)
                maps = []
                for f in image_files:
                    if f == preview:
                        continue
                    channel = next((v for k, v in [('albedo', 'Albedo'), ('basecolor', 'Albedo'), ('diffuse', 'Albedo'), ('normal', 'Normal'), ('roughness', 'Roughness'), ('displacement', 'Displacement'), ('height', 'Displacement'), ('metalness', 'Metalness'), ('metallic', 'Metalness'), ('_ao', 'AO'), ('opacity', 'Opacity'), ('specular', 'Specular'), ('gloss', 'Gloss')] if k in f.name.lower()), 'Other')
                    maps.append({'name': f.name, 'channel': channel, 'bytes': f.stat().st_size, 'ext': f.suffix[1:].upper()})
                preview = preview or next((f for f in image_files if 'albedo' in f.name.lower()), image_files[0])
                cat = folder.name.split('_')[0] or 'Other'
                if cat not in CATEGORIES:
                    cat = 'Other'
                display = str(meta.get('name') or re.sub('_[^_]+_\\d+K_.*$', '', folder.name).replace('_', ' ')).strip().title()
                tags = [str(t) for t in meta.get('tags', []) if isinstance(t, (str, int))]
                cats = [str(c) for c in meta.get('categories', []) if isinstance(c, str)]
                translated = ' '.join((WORDS.get(w, w) for w in re.findall('[a-z]+', ' '.join([display, folder.name] + tags + cats).lower())))
                resolution = re.search('(?:^|_)(\\d+)K(?:_|$)', folder.name, re.I)
                ident = hashlib.sha1(folder.name.encode()).hexdigest()[:16]
                details = {m['key']: m.get('value') for m in meta.get('meta', []) if isinstance(m, dict) and 'key' in m}
                item = {'id': ident, 'name': display, 'folder': folder.name, 'assetId': str(meta.get('id') or (meta_file.stem if meta_file else ident)), 'category': cat, 'categoryZh': CATEGORIES[cat], 'tags': tags, 'categories': cats, 'search': translated, 'resolution': resolution.group(1) + 'K' if resolution else '—', 'preview': preview.name, 'maps': maps, 'bytes': sum((f.stat().st_size for f in files)), 'modified': folder.stat().st_mtime, 'meta': details}
                item = material_names.apply_metadata(item, folder / '.surface-studio.json')
                if item['category'] not in CATEGORIES:
                    item['category'] = cat
                item['categoryZh'] = CATEGORIES[item['category']]
                result.append(item)
            except (OSError, ValueError, TypeError) as exc:
                warnings.append(f'{folder.name}: {exc}')
        if normal_root:
            result.extend(scan_normals(normal_root, warnings))
        result.extend(scan_decals(configuration.get('decalRoot', ''), warnings))
        result.extend(scan_blender_materials([str(root), *configuration.get('blenderRoots', []), *([configuration['materialSaveRoot']] if configuration.get('materialSaveRoot') else [])], warnings))
        if not result:
            warnings.append('未找到可导入素材：普通库需要“库/材质文件夹/贴图”结构；单张法线请使用法线贴图库。支持 JPG、JPEG、PNG、TIF、TIFF、EXR。')
        counts = Counter((a['category'] for a in result))
        new_index = {'assets': result, 'categories': [{'id': k, 'name': CATEGORIES[k], 'count': v} for k, v in counts.most_common()], 'root': str(root), 'normalRoot': normal_root, 'decalRoot': configuration.get('decalRoot', ''), 'blenderRoots': configuration.get('blenderRoots', []), 'materialSaveRoot': configuration.get('materialSaveRoot', ''), 'scannedAt': time.time(), 'totalBytes': sum((a['bytes'] for a in result)), 'warnings': warnings}
        with APP.LOCK:
            if configuration == APP.CONFIG:
                save_json(APP.DATA / 'index.json', new_index)
                APP.INDEX = new_index
                APP.ASSETS = {a['id']: a for a in result}
    except Exception as exc:
        with APP.LOCK:
            if configuration == APP.CONFIG: APP.SCAN_ERROR = str(exc)
    finally:
        with APP.LOCK:
            APP.SCANNING = False
            changed = configuration != APP.CONFIG
        if changed: threading.Thread(target=scan, daemon=True).start()

def asset_file(ident, name):
    a = APP.ASSETS.get(ident)
    if not a:
        raise ValueError('材质不存在')
    allowed = {a['preview']} | {m['name'] for m in a['maps']}
    if a.get('kind') == 'blend':
        allowed.add(a['blendFile'])
    if name not in allowed:
        raise ValueError('文件不存在')
    root = Path(a.get('sourceRoot') or APP.INDEX['root']).resolve()
    allowed_roots = [APP.INDEX['root'], *APP.INDEX.get('blenderRoots', []), *([APP.INDEX['materialSaveRoot']] if APP.INDEX.get('materialSaveRoot') else [])] if a.get('kind') == 'blend' else [APP.INDEX.get('normalRoot') or APP.INDEX['root']]
    if a.get('kind') == 'decal':
        allowed_roots = [APP.INDEX.get('decalRoot', '')]
    if a.get('sourceRoot') and root not in [Path(r).resolve() for r in allowed_roots]:
        raise ValueError('素材来源不匹配，请重新扫描')
    path = (root / a['folder'] / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('无效路径')
    return path

class Handler(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def send(self, body, mime='application/json; charset=utf-8', status=200, cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public, max-age=86400' if cache else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == '/api/health':
                return self.send({'app': 'Surface Studio', 'ready': True, 'instance': APP.TOKEN})
            if url.path == '/api/library':
                with APP.LOCK:
                    return self.send({**categorized_library(), 'state': APP.STATE, 'token': APP.TOKEN, 'scanning': APP.SCANNING, 'error': APP.SCAN_ERROR, 'releaseNotes': NOTES, 'releaseNotesSeen': read_json(APP.DATA / 'release-notes.json', {}).get('seenVersion') == NOTES['version']})
            if url.path == '/api/status':
                return self.send({'scanning': APP.SCANNING, 'error': APP.SCAN_ERROR, 'count': len(APP.ASSETS)})
            if url.path == '/api/state':
                return self.send(APP.STATE)
            if url.path == '/api/blender/status':
                return self.send({'sessions': APP.BRIDGE.sessions(), 'protocol': 1, 'scannedAt': APP.INDEX.get('scannedAt')})
            if url.path == '/api/blender/result':
                return self.send(APP.BRIDGE.result(q.get('id', [''])[0]))
            if url.path == '/api/image':
                path = asset_file(q.get('id', [''])[0], q.get('file', [''])[0])
                size = min(2048, max(64, int(q.get('size', ['480'])[0])))
                key = hashlib.sha1(f'v2|{path}|{path.stat().st_mtime_ns}|{size}'.encode()).hexdigest()
                cached = APP.CACHE / (key + '.webp')
                if not cached.exists():
                    with APP.THUMB_LOCK:
                        if not cached.exists():
                            with Image.open(path) as raw:
                                im = ImageOps.exif_transpose(raw)
                                im.thumbnail((size, size), Image.Resampling.LANCZOS)
                                if im.mode not in ('RGB', 'RGBA'):
                                    im = im.convert('RGBA')
                                buf = io.BytesIO()
                                im.save(buf, 'WEBP', quality=88, method=4)
                                temp = cached.with_suffix('.' + secrets.token_hex(6) + '.tmp')
                                temp.write_bytes(buf.getvalue())
                                temp.replace(cached)
                return self.send(cached.read_bytes(), 'image/webp', cache=True)
            if url.path == '/api/file':
                path = asset_file(q.get('id', [''])[0], q.get('file', [''])[0])
                return self.send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream', cache=True)
            static = '/index.html' if url.path == '/' else unquote(url.path)
            public = BASE / 'public'
            path = (public / static.lstrip('/')).resolve()
            if not path.is_relative_to(public.resolve()) or not path.is_file():
                return self.send({'error': '未找到页面'}, status=404)
            return self.send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        except (OSError, ValueError) as exc:
            return self.send({'error': str(exc)}, status=400)

    def do_POST(self):
        if self.headers.get('X-Studio-Token') != APP.TOKEN:
            return self.send({'error': '会话已过期，请刷新'}, status=403)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{APP.PORT}', f'http://localhost:{APP.PORT}'):
            return self.send({'error': '无效来源'}, status=403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 16 * 1024 * 1024:
                raise ValueError('请求过大')
            body = json.loads(self.rfile.read(length) or '{}')
            endpoint = urlparse(self.path).path
            with APP.LOCK:
                if endpoint == '/api/release-notes/seen':
                    if body.get('version') != NOTES['version']:
                        raise ValueError('版本号不匹配')
                    save_json(APP.DATA / 'release-notes.json', {'seenVersion': NOTES['version']})
                    return self.send({'ok': True})
                organizer.recover(APP)
                if endpoint == '/api/organize':
                    return self.send(organizer.handle(APP, body))
                if endpoint == '/api/material/rename':
                    return self.send(material_names.rename_material(APP, body.get('id'), body.get('name')))
                if endpoint == '/api/blender/connect':
                    APP.BRIDGE.write(APP.BRIDGE.root / 'connect-request.json', {'id': secrets.token_hex(16), 'created': time.time(), 'expires': time.time() + 15})
                    return self.send({'ok': True})
                if endpoint == '/api/categories':
                    return self.send(edit_category(body))
                if endpoint in ('/api/blender/apply', '/api/blender/drop'):
                    a = APP.ASSETS.get(body.get('asset'))
                    if not a:
                        raise ValueError('材质不存在，请刷新素材库')
                    maps = []
                    for m in a['maps']:
                        path = asset_file(a['id'], m['name'])
                        if not path.is_file():
                            raise ValueError('贴图已移动或丢失，请重新扫描素材库')
                        maps.append({**m, 'path': str(path)})
                    manifest = {'id': a['id'], 'name': a['name'], 'assetId': a['assetId'], 'root': a.get('sourceRoot') or APP.INDEX['root'], 'folder': a['folder'], 'maps': maps}
                    if a.get('kind') == 'decal':
                        manifest['kind'] = 'decal'
                        if endpoint != '/api/blender/drop':
                            raise ValueError('贴花请拖到 Blender 模型表面，原材质不会被替换')
                    if a.get('kind') == 'blend':
                        manifest['kind'] = 'blend'
                        manifest['native'] = {'path': str(asset_file(a['id'], a['blendFile'])), 'materialName': a['materialName'], 'blenderVersion': a['blenderVersion']}
                    if endpoint == '/api/blender/drop':
                        return self.send(APP.BRIDGE.prepare_drop(manifest, body.get('options', {})))
                    return self.send(APP.BRIDGE.enqueue(body.get('session'), manifest, body.get('options', {}), body.get('revision')))
                if endpoint == '/api/state':
                    for key in ('favorites', 'collections', 'recent'):
                        if key in body:
                            if not isinstance(body[key], list):
                                raise ValueError('无效数据')
                            APP.STATE[key] = body[key]
                    save_json(APP.DATA / 'state.json', APP.STATE)
                    return self.send(APP.STATE)
                if endpoint == '/api/open':
                    a = APP.ASSETS.get(body.get('id'))
                    if not a:
                        raise ValueError('材质不存在')
                    path = asset_file(a['id'], a['preview']).parent
                    os.startfile(str(path))
                    return self.send({'ok': True})
                if endpoint == '/api/blender/library-source':
                    directory = body.get('directory')
                    if not isinstance(directory, str) or not Path(directory).is_absolute() or (not Path(directory).is_dir()):
                        raise ValueError('请选择有效的 Blender 材质存放目录')
                    known = [APP.CONFIG['root'], *APP.CONFIG.get('blenderRoots', [])]
                    if APP.CONFIG.get('materialSaveRoot'):
                        known.append(APP.CONFIG['materialSaveRoot'])
                    covered = any((Path(directory).resolve().is_relative_to(Path(p).resolve()) for p in known))
                    body = {} if covered else {'blenderRoots': [*APP.CONFIG.get('blenderRoots', []), directory]}
                    endpoint = '/api/rescan'
                if endpoint == '/api/rescan':
                    if APP.SCANNING:
                        raise ValueError('正在扫描，请稍候')
                    root = body.get('root', APP.CONFIG['root'])
                    if not isinstance(root, str) or not Path(root).is_dir():
                        raise ValueError('路径不存在，请输入完整的材质库文件夹路径')
                    decal_root = body.get('decalRoot', APP.CONFIG.get('decalRoot', ''))
                    if not isinstance(decal_root, str) or (decal_root.strip() and (not Path(decal_root.strip()).is_dir())):
                        raise ValueError('贴花库路径不存在')
                    decal_root = str(Path(decal_root.strip()).resolve()) if decal_root.strip() else ''
                    if decal_root and Path(decal_root) == Path(root).resolve():
                        raise ValueError('贴花库请使用独立目录，不与普通材质库相同')
                    normal_root = body.get('normalRoot', APP.CONFIG.get('normalRoot', ''))
                    if not isinstance(normal_root, str):
                        raise ValueError('法线贴图库路径无效')
                    normal_root = normal_root.strip()
                    if normal_root:
                        if not Path(normal_root).is_dir():
                            raise ValueError('法线贴图库路径不存在，请输入完整文件夹路径')
                        normal_root = str(Path(normal_root).resolve())
                        if decal_root and (Path(decal_root).is_relative_to(Path(normal_root)) or Path(normal_root).is_relative_to(Path(decal_root))):
                            raise ValueError('贴花库不能与纯法线目录重叠')
                        if Path(root).resolve().is_relative_to(Path(normal_root)):
                            raise ValueError('法线贴图库应使用独立文件夹，不能包含普通素材库')
                    blender_roots = body.get('blenderRoots', APP.CONFIG.get('blenderRoots', []))
                    if not isinstance(blender_roots, list) or len(blender_roots) > 32:
                        raise ValueError('Blender 材质目录最多 32 个')
                    validated_roots = []
                    for source in blender_roots:
                        if not isinstance(source, str) or not Path(source).is_absolute() or (not Path(source).is_dir()):
                            raise ValueError('Blender 材质库路径不存在，请填写完整目录')
                        resolved = str(Path(source).resolve())
                        if normal_root and (Path(resolved).is_relative_to(Path(normal_root)) or Path(normal_root).is_relative_to(Path(resolved))):
                            raise ValueError('Blender 材质库不能与纯法线目录重叠')
                        if os.path.normcase(resolved) not in [os.path.normcase(v) for v in validated_roots]:
                            validated_roots.append(resolved)
                    save_root = body.get('materialSaveRoot', APP.CONFIG.get('materialSaveRoot', ''))
                    if not isinstance(save_root, str):
                        raise ValueError('材质保存位置无效')
                    save_root = save_root.strip()
                    if save_root:
                        if not Path(save_root).is_absolute() or not Path(save_root).is_dir():
                            raise ValueError('材质保存位置不存在，请填写完整文件夹路径')
                        save_root = str(Path(save_root).resolve())
                        if normal_root and (Path(save_root).is_relative_to(Path(normal_root)) or Path(normal_root).is_relative_to(Path(save_root))):
                            raise ValueError('材质保存位置不能与纯法线目录重叠')
                    APP.CONFIG['materialSaveRoot'] = save_root
                    APP.CONFIG['blenderRoots'] = validated_roots
                    APP.CONFIG['root'] = str(Path(root).resolve())
                    APP.CONFIG['normalRoot'] = normal_root
                    APP.CONFIG['decalRoot'] = decal_root
                    save_json(APP.DATA / 'config.json', APP.CONFIG)
                    threading.Thread(target=scan, daemon=True).start()
                    return self.send({'ok': True})
            return self.send({'error': '未知操作'}, status=404)
        except (ValueError, OSError, TypeError) as exc:
            return self.send({'error': str(exc)}, status=400)
APP.services.update({name: globals()[name] for name in ('read_json','save_json','scan','category_data','categorized_library','CATEGORIES','organizer')})
expose_legacy_state(sys.modules[__name__], APP)
organizer.recover(APP)

if __name__ == '__main__':
    saved = read_json(APP.DATA / 'index.json', None)
    if saved and saved.get('decalRoot', '') == APP.CONFIG.get('decalRoot', '') and (saved.get('root') == APP.CONFIG['root']) and (saved.get('normalRoot', '') == APP.CONFIG.get('normalRoot', '')) and (saved.get('blenderRoots', []) == APP.CONFIG.get('blenderRoots', [])) and (saved.get('materialSaveRoot', '') == APP.CONFIG.get('materialSaveRoot', '')):
        APP.INDEX = saved
        APP.ASSETS = {a['id']: a for a in APP.INDEX['assets']}
    else:
        scan()
    print(f'Surface Studio http://127.0.0.1:{APP.PORT} | {len(APP.ASSETS)} materials', flush=True)
    ThreadingHTTPServer(('127.0.0.1', APP.PORT), Handler).serve_forever()
