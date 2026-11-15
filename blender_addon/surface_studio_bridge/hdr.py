"""Apply an HDR to the active scene without editing an existing/shared World."""
from pathlib import Path

import bpy


def apply_environment(context, manifest):
    maps = manifest.get('maps', [])
    if manifest.get('kind') != 'hdr' or len(maps) != 1 or maps[0].get('channel') != 'Environment':
        raise ValueError('HDR 环境数据无效，请从 SS 重新拖出')
    entry = maps[0]
    root = Path(manifest.get('root', '')).resolve()
    path = Path(entry.get('path', '')).resolve()
    expected = (root / manifest.get('folder', '.') / entry.get('name', '')).resolve()
    if path != expected or not path.is_relative_to(root) or path.suffix.lower() not in ('.hdr', '.exr'):
        raise ValueError('HDR 环境文件路径无效')
    if not path.is_file():
        raise ValueError('HDR 环境图已移动或丢失，请重新扫描 SS')
    scene = context.scene
    if not scene or not scene.is_editable:
        raise ValueError('当前场景不可编辑')
    old_world = scene.world
    old_fake_user = old_world.use_fake_user if old_world else False
    existing_images = set(bpy.data.images)
    image = world = None
    shading = context.space_data.shading if context.space_data and context.space_data.type == 'VIEW_3D' else None
    old_shading = (shading.type, shading.use_scene_world, shading.use_scene_world_render) if shading else None
    try:
        # A preexisting image may contain unsaved pixels or user color-space edits.
        image = bpy.data.images.load(str(path), check_existing=False)
        if min(image.size) <= 0:
            raise ValueError('无法解码 HDR 环境图')
        world = bpy.data.worlds.new('SS HDR · ' + str(manifest.get('name') or path.stem))
        world.use_nodes = True
        nodes = world.node_tree.nodes
        nodes.clear()
        environment = nodes.new('ShaderNodeTexEnvironment')
        environment.image = image
        environment.projection = 'EQUIRECTANGULAR'
        environment.location = (-320, 0)
        background = nodes.new('ShaderNodeBackground')
        background.inputs['Strength'].default_value = 1.0
        background.location = (-40, 0)
        output = nodes.new('ShaderNodeOutputWorld')
        output.location = (200, 0)
        world.node_tree.links.new(environment.outputs['Color'], background.inputs['Color'])
        world.node_tree.links.new(background.outputs['Background'], output.inputs['Surface'])
        scene.world = world
        if old_world:
            old_world.use_fake_user = True  # Preserve it across .blend save/reopen, too.
        if shading:
            shading.use_scene_world = True
            shading.use_scene_world_render = True
            if shading.type in ('SOLID', 'WIREFRAME'):
                shading.type = 'MATERIAL'
        return {'status': 'success', 'world': world.name,
                'message': f'已应用 HDR 环境：{manifest.get("name") or path.stem} · 渲染使用此环境 · Ctrl+Z 可撤销'}
    except Exception:
        scene.world = old_world
        if old_world:
            old_world.use_fake_user = old_fake_user
        if shading:
            shading.type, shading.use_scene_world, shading.use_scene_world_render = old_shading
        if world:
            bpy.data.worlds.remove(world)
        if image and image not in existing_images and image.users == 0:
            bpy.data.images.remove(image)
        raise
