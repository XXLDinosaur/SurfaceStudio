"""Run with a separate --factory-startup Blender and an isolated user profile."""
import json
import sys
import tempfile
import time
from pathlib import Path

import bpy
import addon_utils

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'blender_addon')]
addon = addon_utils.enable('surface_studio_bridge', default_set=True)
assert addon, 'SS plugin could not load'
assert hasattr(addon, 'apply_environment'), 'HDR environment receiver is not implemented'
from blender_bridge import BlenderBridge

source = Path(sys.argv[sys.argv.index('--')+1])
out = Path(sys.argv[sys.argv.index('--')+2]); out.mkdir(parents=True, exist_ok=True)
cases = []
selected = [min(source.rglob('*.'+ext), key=lambda p:p.stat().st_size) for ext in ('hdr','exr')]

def manifest(path):
    return {'kind':'hdr','id':'fixture','assetId':'fixture','name':path.stem,
            'root':str(path.parent),'folder':'.',
            'maps':[{'name':path.name,'path':str(path),'channel':'Environment'}]}

original = bpy.context.scene.world
try:
    addon.apply_environment(bpy.context, manifest(out/'missing.hdr'))
    raise AssertionError('Missing image must fail')
except (ValueError, OSError): pass
assert bpy.context.scene.world == original
assert len(bpy.data.worlds) == 1

with tempfile.TemporaryDirectory(prefix='ss-hdr-plugin-') as directory:
    temp = Path(directory)
    prefs = bpy.context.preferences.addons[addon.__name__].preferences
    prefs.executable_path = str(temp/'Surface Studio.exe')
    (temp/'Surface Studio.exe').touch()
    bridge = BlenderBridge(temp/'data/blender')
    area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    original.use_fake_user = False
    user_image = bpy.data.images.load(str(selected[0]),check_existing=False)
    user_image.scale(1,1)  # Unsaved user edits must not become the SS environment.
    sibling = bpy.data.scenes.new('Shared World Check'); sibling.world = original
    for index,path in enumerate(selected):
        scene = bpy.context.scene
        previous = scene.world
        old_nodes = [(n.name,n.bl_idname) for n in previous.node_tree.nodes]
        before = len(bpy.data.worlds)
        task = bridge.prepare_drop(manifest(path), {})
        # Deliberately no target: this is the receiver path for empty viewport drops.
        with bpy.context.temp_override(area=area,region=region):
            result = bpy.ops.surface_studio.drop_material(filepath=task['path'],target_name='')
        assert result == {'FINISHED'}, result
        state = bridge.result(task['id'])
        assert state['status'] == 'success', state
        world = scene.world
        assert world != previous and len(bpy.data.worlds) == before+1
        assert [(n.name,n.bl_idname) for n in previous.node_tree.nodes] == old_nodes
        assert sibling.world == original
        assert area.spaces.active.shading.use_scene_world
        environment = next(n for n in world.node_tree.nodes if n.type == 'TEX_ENVIRONMENT')
        if index == 0:
            assert environment.image != user_image, 'SS reused a user-edited image buffer'
            assert min(environment.image.size) > 1
            assert tuple(user_image.size) == (1,1)
        assert Path(bpy.path.abspath(environment.image.filepath)).resolve() == path.resolve()
        assert len(world.node_tree.links) == 2
        # A duplicate file must not change the scene again.
        with bpy.context.temp_override(area=area,region=region):
            assert bpy.ops.surface_studio.drop_material(filepath=task['path'],target_name='') == {'CANCELLED'}
        assert scene.world == world
        # Nonexistent and corrupt source fail without leaving a World behind.
        for bad in (out/'missing.hdr', out/'corrupt.hdr'):
            if bad.name.startswith('corrupt'): bad.write_bytes(b'not an image')
            count = len(bpy.data.worlds)
            try: addon.apply_environment(bpy.context, manifest(bad))
            except (ValueError,OSError,RuntimeError): pass
            else: raise AssertionError('Invalid environment accepted')
            assert scene.world == world and len(bpy.data.worlds) == count
        # Render cube with no local lights; only the HDR supplies illumination.
        for obj in list(bpy.data.objects):
            if obj.type == 'LIGHT': bpy.data.objects.remove(obj,do_unlink=True)
        scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
        scene.cycles.device = 'CPU'; scene.cycles.use_denoising = False
        scene.render.resolution_x = 128; scene.render.resolution_y = 128
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(out/f'{index}-receiver-render.png')
        bpy.ops.render.render(write_still=True)
        cycles_render = scene.render.filepath
        eevee_engine = next(e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items if 'EEVEE' in e.identifier)
        scene.render.engine = eevee_engine
        scene.render.filepath = str(out/f'{index}-eevee-render.png')
        bpy.ops.render.render(write_still=True)
        eevee_render = scene.render.filepath
        scene.render.engine = 'CYCLES'
        blend = out/f'{index}-receiver.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        cases.append({'source':str(path),'status':state['status'],'empty_viewport_receiver':True,
                      'shared_world_preserved':True,'duplicate_blocked':True,'invalid_source_rollback':True,
                      'render':cycles_render,'eevee_render':eevee_render,'eevee_engine':eevee_engine,'blend':str(blend)})
    environment_name, original_name = environment.name, original.name
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    assert bpy.context.scene.world.node_tree.nodes.get(environment_name)
    assert bpy.data.scenes['Shared World Check'].world.name == original_name
with tempfile.TemporaryDirectory(prefix='ss-hdr-undo-') as directory:
    temp = Path(directory); (temp/'Surface Studio.exe').touch()
    bpy.context.preferences.addons[addon.__name__].preferences.executable_path = str(temp/'Surface Studio.exe')
    bridge = BlenderBridge(temp/'data/blender')
    area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    old_name = bpy.context.scene.world.name
    task = bridge.prepare_drop(manifest(selected[0]), {})
    bpy.ops.ed.undo_push(message='Before HDR environment')
    with bpy.context.temp_override(area=area,region=region):
        assert bpy.ops.surface_studio.drop_material('EXEC_DEFAULT', True, filepath=task['path'],target_name='') == {'FINISHED'}
    new_name = bpy.context.scene.world.name
    assert new_name != old_name
    assert bpy.ops.ed.undo() == {'FINISHED'}
    assert bpy.context.scene.world.name == old_name
    assert bpy.ops.ed.redo() == {'FINISHED'}
    assert bpy.context.scene.world.name == new_name
report = {'blender':bpy.app.version_string,'cases':cases,'save_reopen':True,
          'full_mouse_gesture_tested':False,'undo_tested':True,'redo_tested':True}
(out/'receiver-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HDR_RECEIVER_PASS '+json.dumps(report,ensure_ascii=False))
