"""Local JSON mailbox. Blender handles all scene changes on its main thread."""
import json
import math
import re
import secrets
import time
from pathlib import Path


class BlenderBridge:
    def __init__(self, root):
        self.root = Path(root)
        for name in ('sessions', 'requests', 'results'):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def read(path):
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None

    @staticmethod
    def write(path, data):
        temp = path.with_suffix('.' + secrets.token_hex(5) + '.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)

    @staticmethod
    def valid_id(value):
        return isinstance(value, str) and bool(re.fullmatch(r'[a-f0-9]{32}', value))

    def sessions(self):
        result = []
        for path in (self.root / 'sessions').glob('*.json'):
            if not self.valid_id(path.stem):
                continue
            session = self.read(path)
            if not isinstance(session, dict):
                continue
            if time.time() - session.get('heartbeat', 0) > 6:
                continue
            if session.get('id') != path.stem:
                continue
            result.append(session)
        return sorted(result, key=lambda s: s.get('heartbeat', 0), reverse=True)

    def enqueue(self, session_id, manifest, options, expected_revision):
        if not self.valid_id(session_id):
            raise ValueError('请选择已连接的 Blender')
        session = next((s for s in self.sessions() if s['id'] == session_id), None)
        if not session:
            raise ValueError('Blender 未连接。请在 Blender 的 Surface Studio 侧栏点击连接。')
        if session.get('revision') != expected_revision:
            raise ValueError('Blender 中的选择已变化，请确认目标模型后重新点击赋予')
        if not session.get('objects'):
            raise ValueError('请先在 Blender 中选择网格模型')
        if session.get('mode') not in ('OBJECT', 'EDIT_MESH'):
            raise ValueError('请切换到对象模式或网格编辑模式')
        if session.get('mode') == 'EDIT_MESH' and not session.get('selectedFaces'):
            raise ValueError('编辑模式下请先选择需要赋予材质的面')
        if not isinstance(options, dict):
            raise ValueError('无效导入选项')
        repeat = float(options.get('repeat', 1))
        if not math.isfinite(repeat) or not 0.01 <= repeat <= 100:
            raise ValueError('贴图平铺次数应在 0.01 到 100 之间')
        opts = {'repeat': repeat, 'autoUV': bool(options.get('autoUV', True)),
                'ao': bool(options.get('ao', True)), 'bump': bool(options.get('bump', False)),
                'flipNormalY': bool(options.get('flipNormalY', False))}
        request_path = self.root / 'requests' / (session_id + '.json')
        previous = self.read(request_path)
        if previous and previous.get('expires', 0) > time.time():
            raise ValueError('上一个材质仍在处理中，请稍候')
        # A claimed request is no longer on disk; its session stays busy until completion.
        if session.get('busy'):
            raise ValueError('Blender 正在导入材质，请稍候')
        ident = secrets.token_hex(16)
        job = {'id': ident, 'session': session_id, 'created': time.time(),
               'expires': time.time() + 30, 'revision': session['revision'],
               'material': manifest, 'options': opts}
        self.write(self.root / 'results' / (ident + '.json'),
                   {'id': ident, 'status': 'pending', 'created': job['created'], 'message': '等待 Blender 接收…'})
        self.write(request_path, job)
        return {'id': ident, 'status': 'pending'}

    def result(self, ident):
        if not self.valid_id(ident):
            raise ValueError('无效任务编号')
        result = self.read(self.root / 'results' / (ident + '.json'))
        if not result:
            raise ValueError('导入任务不存在')
        if result.get('status') == 'pending' and time.time() - result.get('created', 0) > 35:
            return {**result, 'status': 'error', 'message': 'Blender 未及时接收。请确认插件已连接后重试。'}
        if result.get('status') == 'applying' and time.time() - result.get('updated', 0) > 180:
            return {**result, 'status': 'unknown', 'message': 'Blender 暂未返回结果，请先在 Blender 中检查材质；确认后再重试。'}
        return result
