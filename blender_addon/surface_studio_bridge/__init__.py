bl_info = {
    'name': 'Surface Studio — 本地材质库',
    'author': 'Surface Studio',
    'version': (1, 0, 0),
    'blender': (4, 2, 0),
    'location': '3D Viewport > Sidebar > Surface Studio',
    'description': '打开 Surface Studio，将本地 PBR 材质一键赋予选中模型或选中的面',
    'category': 'Material',
}

import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import bpy
import bmesh
from bpy.props import StringProperty
from bpy.types import AddonPreferences, Operator, Panel
from bpy.app.handlers import persistent

DEFAULT_EXE = str(Path.home() / 'SurfaceStudio' / 'Surface Studio.exe')
SESSION = uuid.uuid4().hex
CONNECTED = False
BUSY = False
LAST_MESSAGE = '点击「打开材质库」开始使用'
MAILBOX = None
LOAD_GENERATION = 0
APPLY_RESULT = None


def atomic_json(path, data):
    temp = path.with_suffix('.' + uuid.uuid4().hex[:10] + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def executable():
    addon = bpy.context.preferences.addons.get(__name__)
    return Path(bpy.path.abspath(addon.preferences.executable_path if addon else DEFAULT_EXE)).resolve()


def snapshot():
    context = bpy.context
    meshes = sorted((o for o in context.selected_objects if o.type == 'MESH'), key=lambda o: o.name)
    objects = [{'name': o.name, 'key': str(o.as_pointer()), 'hasUV': bool(o.data.uv_layers)} for o in meshes]
    faces = []
    if context.mode == 'EDIT_MESH':
        for obj in meshes:
            if obj.mode != 'EDIT':
                continue
            mesh = bmesh.from_edit_mesh(obj.data)
            mesh.faces.ensure_lookup_table()
            mesh.faces.index_update()
            faces.append((obj.name, [f.index for f in mesh.faces if f.select]))
    state = {'mode': context.mode, 'objects': objects,
             'scene': str(context.scene.as_pointer()), 'generation': LOAD_GENERATION,
             'active': context.view_layer.objects.active.name if context.view_layer.objects.active else '',
             'faces': faces}
    revision = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return {'id': SESSION, 'heartbeat': time.time(), 'revision': revision, 'objects': objects,
            'mode': context.mode, 'selectedFaces': sum(len(f[1]) for f in faces),
            'file': Path(bpy.data.filepath).name if bpy.data.filepath else '未保存的场景',
            'version': bpy.app.version_string, 'pid': os.getpid(), 'busy': BUSY,
            'message': LAST_MESSAGE, 'protocol': 1}


def publish():
    if MAILBOX:
        atomic_json(MAILBOX / 'sessions' / (SESSION + '.json'), snapshot())


def refresh_panels():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def connect():
    global CONNECTED, MAILBOX, LAST_MESSAGE
    exe = executable()
    if not exe.is_file():
        raise ValueError('未找到 Surface Studio.exe，请在插件偏好设置中选择软件路径')
    MAILBOX = exe.parent / 'data' / 'blender'
    for directory in ('sessions', 'requests', 'results'):
        (MAILBOX / directory).mkdir(parents=True, exist_ok=True)
    CONNECTED = True
    LAST_MESSAGE = '已连接，选中模型后在材质库中点击赋予'
    publish()
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=0.4, persistent=True)


def disconnect():
    global CONNECTED, LAST_MESSAGE
    CONNECTED = False
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if MAILBOX:
        for directory in ('sessions', 'requests'):
            path = MAILBOX / directory / (SESSION + '.json')
            if path.exists():
                path.unlink()
    LAST_MESSAGE = '连接已断开'


def validate_job(job):
    if job.get('session') != SESSION:
        raise ValueError('任务不属于当前 Blender 窗口')
    if job.get('expires', 0) < time.time():
        raise ValueError('任务已过期，请重新点击赋予')
    current = snapshot()
    if current['revision'] != job.get('revision'):
        raise ValueError('选中的模型或面已变化，本次未赋予材质。请重新点击赋予。')
    if current['mode'] not in ('OBJECT', 'EDIT_MESH') or not current['objects']:
        raise ValueError('请在对象模式或编辑模式选择网格模型')
    if current['mode'] == 'EDIT_MESH' and not current['selectedFaces']:
        raise ValueError('请先选中需要赋材质的面')
    objects = [bpy.context.view_layer.objects[item['name']] for item in current['objects']]
    for obj in objects:
        if not obj.is_editable or not obj.data.is_editable:
            raise ValueError(f'{obj.name} 是只读链接对象，请先本地化')
        if current['mode'] == 'EDIT_MESH' and obj.data.users > 1:
            raise ValueError(f'{obj.name} 与其他对象共享网格，请先使其独立后再给选中面赋材质')
    opts = job.get('options', {})
    repeat = float(opts.get('repeat', 1))
    if not math.isfinite(repeat) or not 0.01 <= repeat <= 100:
        raise ValueError('无效贴图平铺次数')
    for obj in objects:
        if not obj.data.uv_layers:
            if current['mode'] == 'EDIT_MESH' or not opts.get('autoUV', True):
                raise ValueError(f'{obj.name} 没有 UV，请先展开 UV，或在对象模式启用自动 UV')
    manifest = job.get('material', {})
    root = Path(manifest.get('root', '')).resolve()
    folder = (root / manifest.get('folder', '')).resolve()
    if not folder.is_relative_to(root):
        raise ValueError('无效材质路径')
    for texture in manifest.get('maps', []):
        path = Path(texture.get('path', '')).resolve()
        if not path.is_relative_to(folder) or not path.is_file():
            raise ValueError('贴图丢失或路径不在当前材质目录中')
        if path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.exr'):
            raise ValueError('不支持的贴图格式')
    if not manifest.get('maps'):
        raise ValueError('该材质没有可用贴图')
    return objects, opts


def choose_maps(manifest, opts):
    grouped = {}
    for m in manifest['maps']:
        grouped.setdefault(m['channel'], []).append(m)
    selected = {}
    # Prefer compact maps for interactive import; height EXR only when bump is requested.
    for channel, values in grouped.items():
        if channel == 'Displacement' and not opts.get('bump'):
            continue
        order = ['EXR', 'PNG', 'TIF', 'TIFF', 'JPG', 'JPEG'] if channel == 'Displacement' else ['PNG', 'JPG', 'JPEG', 'TIF', 'TIFF', 'EXR']
        values.sort(key=lambda m: order.index(m['ext']) if m['ext'] in order else 99)
        selected[channel] = values[0]
    return selected


def build_material(manifest, opts):
    signature = hashlib.sha256(json.dumps({'id': manifest['id'], 'folder': manifest['folder'],
        'root': manifest['root'], 'options': opts}, sort_keys=True).encode()).hexdigest()
    # Reuse only our material for the same asset/options, never replace another shader graph.
    existing = next((m for m in bpy.data.materials if m.get('surface_studio_signature') == signature), None)
    if existing:
        return existing, []
    material = bpy.data.materials.new('SS · ' + manifest['name'])
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    shader = nodes.new('ShaderNodeBsdfPrincipled'); shader.location = (470, 100)
    output = nodes.new('ShaderNodeOutputMaterial'); output.location = (800, 100)
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    texcoord = nodes.new('ShaderNodeTexCoord'); texcoord.location = (-1050, 200)
    mapping = nodes.new('ShaderNodeMapping'); mapping.location = (-840, 200)
    mapping.label = '平铺次数 / Tiling'
    mapping.inputs['Scale'].default_value = (opts.get('repeat', 1),) * 3
    links.new(texcoord.outputs['UV'], mapping.inputs['Vector'])
    textures = {}
    warnings = []
    try:
        maps = choose_maps(manifest, opts)
        for i, channel in enumerate(('Albedo', 'AO', 'Roughness', 'Metalness', 'Normal', 'Displacement', 'Opacity', 'Specular', 'Gloss', 'Other')):
            if channel not in maps or (channel == 'AO' and not opts.get('ao', True)):
                continue
            texture = nodes.new('ShaderNodeTexImage'); texture.location = (-560, 400 - i * 240)
            texture.label = channel; texture.name = channel
            # Dedicated images protect color-space settings of images already used by other materials.
            image = bpy.data.images.load(maps[channel]['path'], check_existing=False)
            image.colorspace_settings.name = 'sRGB' if channel == 'Albedo' else 'Non-Color'
            texture.image = image
            texture.interpolation = 'Linear'
            texture.extension = 'REPEAT'
            links.new(mapping.outputs['Vector'], texture.inputs['Vector'])
            textures[channel] = texture
        if 'Albedo' in textures:
            color = textures['Albedo'].outputs['Color']
            if 'AO' in textures:
                ao = nodes.new('ShaderNodeMixRGB'); ao.blend_type = 'MULTIPLY'; ao.inputs[0].default_value = 1
                ao.location = (160, 380); ao.label = 'Albedo × AO'
                links.new(color, ao.inputs[1]); links.new(textures['AO'].outputs['Color'], ao.inputs[2])
                color = ao.outputs['Color']
            links.new(color, shader.inputs['Base Color'])
        else:
            warnings.append('该素材无颜色贴图，保留默认底色')
        for channel, socket in (('Roughness', 'Roughness'), ('Metalness', 'Metallic'), ('Opacity', 'Alpha'), ('Specular', 'Specular IOR Level')):
            if channel in textures and socket in shader.inputs:
                links.new(textures[channel].outputs['Color'], shader.inputs[socket])
        if 'Gloss' in textures and 'Roughness' not in textures:
            invert = nodes.new('ShaderNodeMath'); invert.operation = 'SUBTRACT'; invert.inputs[0].default_value = 1
            invert.location = (120, -120); invert.label = 'Gloss → Roughness'
            links.new(textures['Gloss'].outputs['Color'], invert.inputs[1])
            links.new(invert.outputs[0], shader.inputs['Roughness'])
        normal_out = None
        if 'Normal' in textures:
            normal_color = textures['Normal'].outputs['Color']
            if opts.get('flipNormalY'):
                flip = nodes.new('ShaderNodeVectorMath'); flip.operation = 'MULTIPLY_ADD'; flip.location = (-250, -490)
                flip.label = 'DirectX → OpenGL'; flip.inputs[1].default_value = (1, -1, 1); flip.inputs[2].default_value = (0, 1, 0)
                links.new(normal_color, flip.inputs[0]); normal_color = flip.outputs['Vector']
            normal = nodes.new('ShaderNodeNormalMap'); normal.location = (0, -500)
            normal.space = 'TANGENT'; normal.inputs['Strength'].default_value = 1
            links.new(normal_color, normal.inputs['Color']); normal_out = normal.outputs['Normal']
        if 'Displacement' in textures:
            bump = nodes.new('ShaderNodeBump'); bump.location = (230, -450)
            bump.label = 'Height detail · 不改变几何'; bump.inputs['Distance'].default_value = 0.02
            bump.inputs['Strength'].default_value = 0.3
            links.new(textures['Displacement'].outputs['Color'], bump.inputs['Height'])
            if normal_out: links.new(normal_out, bump.inputs['Normal'])
            normal_out = bump.outputs['Normal']
        if normal_out: links.new(normal_out, shader.inputs['Normal'])
        if 'Opacity' in textures and hasattr(material, 'surface_render_method'):
            material.surface_render_method = 'DITHERED'
        if 'Other' in textures:
            warnings.append('未识别用途的贴图已载入节点，未自动接线')
        material['surface_studio_signature'] = signature
        material['surface_studio_asset'] = manifest['assetId']
        material['surface_studio_path'] = str(Path(manifest['root']) / manifest['folder'])
        return material, warnings
    except Exception:
        images = [n.image for n in nodes if n.type == 'TEX_IMAGE' and n.image]
        bpy.data.materials.remove(material)
        for image in images:
            if image.users == 0: bpy.data.images.remove(image)
        raise


def smart_uv(context, obj):
    selected = list(context.selected_objects)
    active = context.view_layer.objects.active
    try:
        for item in selected: item.select_set(False)
        obj.select_set(True); context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    finally:
        if obj.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)
        for item in selected: item.select_set(True)
        context.view_layer.objects.active = active


def apply_job(context, job):
    objects, opts = validate_job(job)
    editing = context.mode == 'EDIT_MESH'
    material, warnings = build_material(job['material'], opts)
    # Keep unselected linked duplicates untouched. Original material slots are retained.
    changed, auto_uv_count, face_count = [], 0, 0
    backups = []
    try:
        for obj in objects:
            if editing:
                mesh = bmesh.from_edit_mesh(obj.data)
                faces = [f for f in mesh.faces if f.select]
                if not faces: continue
                old_indices = [(face, face.material_index) for face in faces]
                slot_count = len(obj.data.materials)
                backups.append(('EDIT', obj, old_indices, slot_count, obj.active_material_index))
            else:
                original = obj.data
                # Work on a private copy for atomic rollback and linked-instance safety.
                obj.data = original.copy()
                backups.append(('OBJECT', obj, original, obj.data, obj.active_material_index))
                if not obj.data.uv_layers:
                    smart_uv(context, obj); auto_uv_count += 1
            index = next((i for i, m in enumerate(obj.data.materials) if m == material), None)
            if index is None:
                obj.data.materials.append(material); index = len(obj.data.materials) - 1
            obj.active_material_index = index
            if editing:
                for face in faces: face.material_index = index
                face_count += len(faces)
                bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
            else:
                for polygon in obj.data.polygons: polygon.material_index = index
                obj.data.update()
                face_count += len(obj.data.polygons)
            changed.append(obj.name)
        if not changed: raise ValueError('没有可赋予材质的选中面')
    except Exception:
        for kind, obj, old, extra, active_slot in reversed(backups):
            if kind == 'OBJECT':
                obj.data = old
                if extra.users == 0: bpy.data.meshes.remove(extra)
            else:
                for face, index in old: face.material_index = index
                while len(obj.data.materials) > extra: obj.data.materials.pop(index=len(obj.data.materials) - 1)
                bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
            obj.active_material_index = active_slot
        raise
    # Main-thread operator invocation supplies the undo step, including mesh copies and UVs.
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D': area.spaces.active.shading.type = 'MATERIAL'
    return {'status': 'success', 'material': material.name, 'objects': changed, 'faces': face_count,
            'autoUV': auto_uv_count, 'warnings': warnings,
            'message': f'已将 {job["material"]["name"]} 赋予 {len(changed)} 个模型' + (f'的 {face_count} 个选中面' if editing else '')}


class SURFACESTUDIO_OT_apply(Operator):
    bl_idname = 'surface_studio.apply_material'
    bl_label = '赋予 Surface Studio 材质'
    bl_options = {'REGISTER', 'UNDO'}
    payload: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        global APPLY_RESULT
        try:
            APPLY_RESULT = apply_job(context, json.loads(self.payload))
            self.report({'INFO'}, APPLY_RESULT['message'])
            return {'FINISHED'}
        except Exception as exc:
            APPLY_RESULT = {'status': 'error', 'message': str(exc)}
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}


def tick():
    global BUSY, LAST_MESSAGE, APPLY_RESULT
    if not CONNECTED: return None
    try:
        publish()
        path = MAILBOX / 'requests' / (SESSION + '.json')
        job = read_json(path)
        if job:
            path.unlink(missing_ok=True)
            ident = job.get('id', '')
            if not re.fullmatch(r'[a-f0-9]{32}', ident):
                raise ValueError('无效导入任务')
            result_path = MAILBOX / 'results' / (ident + '.json')
            previous = read_json(result_path)
            if previous and previous.get('status') in ('success', 'error', 'applying'):
                return 0.5
            BUSY = True
            publish()
            atomic_json(result_path, {'id': ident, 'status': 'applying', 'updated': time.time(), 'message': 'Blender 正在建立材质节点…'})
            APPLY_RESULT = None
            bpy.ops.surface_studio.apply_material('EXEC_DEFAULT', True, payload=json.dumps(job, ensure_ascii=False))
            result = APPLY_RESULT or {'status': 'error', 'message': 'Blender 未完成导入'}
            LAST_MESSAGE = result['message']
            atomic_json(result_path, {**result, 'id': ident, 'updated': time.time()})
            BUSY = False
            publish()
            refresh_panels()
    except Exception as exc:
        BUSY = False
        LAST_MESSAGE = '连接提示：' + str(exc)
    return 0.5


class SURFACESTUDIO_Preferences(AddonPreferences):
    bl_idname = __name__
    executable_path: StringProperty(name='Surface Studio 程序', subtype='FILE_PATH', default=DEFAULT_EXE)

    def draw(self, context):
        self.layout.prop(self, 'executable_path')
        self.layout.label(text='请选择 Surface Studio.exe；所有贴图留在本地。')


class SURFACESTUDIO_OT_open(Operator):
    bl_idname = 'surface_studio.open_library'
    bl_label = '打开材质库'
    bl_description = '连接当前 Blender，并打开 Surface Studio 材质管理器'

    def execute(self, context):
        try:
            connect()
            subprocess.Popen([str(executable())], cwd=str(executable().parent))
            self.report({'INFO'}, '已打开材质库，选好材质后点击「赋予到 Blender」')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}


class SURFACESTUDIO_OT_connect(Operator):
    bl_idname = 'surface_studio.connect'
    bl_label = '连接 / 断开'

    def execute(self, context):
        try:
            if CONNECTED: disconnect()
            else: connect()
            refresh_panels(); return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}


class SURFACESTUDIO_PT_panel(Panel):
    bl_label = 'SURFACE STUDIO'
    bl_idname = 'SURFACESTUDIO_PT_library'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Surface Studio'

    def draw(self, context):
        layout = self.layout
        layout.label(text='你的私人 PBR 材质库', icon='MATERIAL')
        row = layout.row(); row.scale_y = 1.6
        row.operator('surface_studio.open_library', icon='ASSET_MANAGER')
        row = layout.row()
        row.label(text='已连接' if CONNECTED else '未连接', icon='LINKED' if CONNECTED else 'UNLINKED')
        row.operator('surface_studio.connect', text='断开' if CONNECTED else '连接')
        box = layout.box()
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        box.label(text=f'已选中 {len(meshes)} 个网格模型', icon='OUTLINER_OB_MESH')
        box.label(text='编辑模式：仅赋予选中面' if context.mode == 'EDIT_MESH' else '对象模式：赋予整个选中模型')
        box.label(text='Ctrl + Z 可撤销赋予操作', icon='LOOP_BACK')
        if LAST_MESSAGE:
            col = layout.column(align=True)
            for start in range(0, len(LAST_MESSAGE), 24): col.label(text=LAST_MESSAGE[start:start + 24])
        layout.separator()
        layout.label(text='贴图缩放、法线方向在材质库中设置')


@persistent
def on_load(_):
    global LOAD_GENERATION
    LOAD_GENERATION += 1
    if CONNECTED:
        try: publish()
        except OSError: pass


CLASSES = (SURFACESTUDIO_Preferences, SURFACESTUDIO_OT_apply, SURFACESTUDIO_OT_open,
           SURFACESTUDIO_OT_connect, SURFACESTUDIO_PT_panel)


def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    if on_load not in bpy.app.handlers.load_post: bpy.app.handlers.load_post.append(on_load)


def unregister():
    disconnect()
    if on_load in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(on_load)
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)


if __name__ == '__main__': register()
