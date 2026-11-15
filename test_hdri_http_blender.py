"""Headless SS HTTP -> .ssmat -> Blender receiver integration (no OS input)."""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--')+1:]
ss_root, output = [Path(arg).resolve() for arg in args[:2]]
output.mkdir(parents=True, exist_ok=True)
discovery = json.loads((ss_root/'data/service.json').read_text(encoding='utf-8'))
base = 'http://127.0.0.1:' + str(discovery['port'])
token = None

def request(path, body=None):
    headers = {'Content-Type': 'application/json'}
    if body is not None: headers['X-Studio-Token'] = token
    with urlopen(Request(base+path, data=None if body is None else json.dumps(body).encode(), headers=headers), timeout=30) as response:
        return json.load(response)

health = request('/api/health')
assert health['app'] == 'Surface Studio' and health['ready'] and health['instance'] == discovery['instance']
library = request('/api/library')
assert not library['scanning'] and not library['error']
token = library['token']
assets = [asset for asset in library['assets'] if asset.get('kind') == 'hdr']
assert assets, 'Test SS has no HDR assets'
selected = [min((asset for asset in assets if asset['maps'][0]['ext'] == ext), key=lambda asset: asset['bytes']) for ext in ('HDR','EXR')]
sys.path.insert(0, str(ROOT/'blender_addon'))
addon = addon_utils.enable('surface_studio_bridge', default_set=True)
assert addon.bl_info['version'] == (1,4,0)
bpy.context.preferences.addons[addon.__name__].preferences.executable_path = str(ss_root/'Surface Studio.exe')
scene = bpy.context.scene
original_world = scene.world
sibling = bpy.data.scenes.new('HTTP Shared World'); sibling.world = original_world
original_world_name = original_world.name
cube = bpy.data.objects['Cube']
original_materials = tuple(cube.data.materials)
for obj in bpy.context.selected_objects: obj.select_set(False)
bpy.context.view_layer.objects.active = None
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT': bpy.data.objects.remove(obj, do_unlink=True)
scene.render.resolution_x = 320; scene.render.resolution_y = 240
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.cycles.samples = 8; scene.cycles.device = 'CPU'; scene.cycles.use_denoising = False

def render(path, engine):
    scene.render.engine = engine
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = image.pixels[:]
    values = [pixels[(y*width+x)*4+c] for y in range(height//2-3,height//2+3)
              for x in range(width//2-3,width//2+3) for c in range(3)]
    bpy.data.images.remove(image)
    return sum(values)/len(values)

cases = []
for index, asset in enumerate(selected):
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    region = next(region for region in area.regions if region.type == 'WINDOW')
    previous_name = scene.world.name
    drop = request('/api/blender/drop', {'asset':asset['id'], 'options':{}})
    data = json.loads(Path(drop['path']).read_text(encoding='utf-8'))
    assert data['protocol'] == 3 and data['material']['kind'] == 'hdr'
    bpy.ops.ed.undo_push(message='Before HTTP HDR')
    with bpy.context.temp_override(area=area,region=region):
        assert bpy.ops.surface_studio.drop_material('EXEC_DEFAULT',True,filepath=drop['path'],target_name='') == {'FINISHED'}
    result = request('/api/blender/result?id='+drop['id'])
    assert result['status'] == 'success', result
    world_name = scene.world.name
    env = next(node for node in scene.world.node_tree.nodes if node.type == 'TEX_ENVIRONMENT')
    expected_path = Path(data['material']['maps'][0]['path']).resolve()
    assert Path(bpy.path.abspath(env.image.filepath)).resolve() == expected_path
    assert tuple(cube.data.materials) == original_materials
    assert sibling.world.name == original_world_name
    assert not bpy.context.selected_objects and bpy.context.view_layer.objects.active is None
    assert area.spaces.active.shading.use_scene_world
    assert bpy.ops.ed.undo() == {'FINISHED'}
    assert bpy.context.scene.world.name == previous_name
    assert bpy.ops.ed.redo() == {'FINISHED'}
    scene = bpy.context.scene
    assert scene.world.name == world_name
    # Undo rebinds Blender data; resolve datablocks anew.
    cube = bpy.data.objects['Cube']; sibling = bpy.data.scenes['HTTP Shared World']
    original_materials = tuple(cube.data.materials)
    background = next(node for node in scene.world.node_tree.nodes if node.type == 'BACKGROUND')
    background.inputs['Strength'].default_value = 0
    off = render(output/f'{index}-off.png', 'CYCLES')
    background.inputs['Strength'].default_value = 1
    on = render(output/f'{index}-cycles.png', 'CYCLES')
    assert on > off+.01, (off,on)
    eevee = next(engine.identifier for engine in scene.render.bl_rna.properties['engine'].enum_items if 'EEVEE' in engine.identifier)
    eevee_mean = render(output/f'{index}-eevee.png', eevee)
    assert eevee_mean > off+.01, (off,eevee_mean)
    cases.append({'asset':asset['name'],'format':asset['maps'][0]['ext'],
                  'image':str(expected_path),'api_result':result['status'],
                  'no_selected_objects':True,'cube_material_preserved':True,'shared_world_preserved':True,
                  'undo_redo':True,'center_mean':{'off':off,'cycles':on,'eevee':eevee_mean}})

blend = output/'HDR HTTP TEST.blend'
expected_world = bpy.context.scene.world.name
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.wm.open_mainfile(filepath=str(blend))
assert bpy.context.scene.world.name == expected_world
assert bpy.data.scenes['HTTP Shared World'].world.name == original_world_name
report = {'blender':bpy.app.version_string,'hdr_library_count':len(assets),'cases':cases,
          'save_reopen':True,'os_input_used':False,'full_mouse_gesture_tested':False,'blend':str(blend)}
(output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HDR_HTTP_INTEGRATION_PASS '+json.dumps(report,ensure_ascii=False))
