"""Run with Blender --background --factory-startup --python test_blender.py.
Uses generated tiny test maps and a temporary mailbox, never user models/preferences.
"""
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path
import bpy
import bmesh

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'blender_addon'))
import surface_studio_bridge as addon

checks = []

def check(value, message):
    assert value, message
    checks.append(message)


def main():
    addon.register()
    with tempfile.TemporaryDirectory(prefix='surface_blender_test_') as directory:
        root = Path(directory)
        folder = root / '中文 材质'; folder.mkdir()
        maps = []
        for channel, color in [('Albedo', (.5,.2,.1,1)), ('Normal',(.5,.5,1,1)), ('Roughness',(.6,.6,.6,1)), ('AO',(1,1,1,1)), ('Displacement',(.5,.5,.5,1))]:
            img=bpy.data.images.new('test_'+channel, width=8, height=8)
            img.generated_color=color
            img.filepath_raw=str(folder/(channel+'.png')); img.file_format='PNG'; img.save()
            bpy.data.images.remove(img)
            maps.append({'channel':channel,'name':channel+'.png','path':str(folder/(channel+'.png')),'ext':'PNG'})
        manifest={'id':'test_asset','assetId':'test_id','name':'Test Surface','root':str(root),'folder':folder.name,'maps':maps}
        options={'repeat':2,'autoUV':True,'ao':True,'bump':True,'flipNormalY':True}
        cube=bpy.data.objects['Cube']
        original=bpy.data.materials.new('Original Material')
        cube.data.materials.clear(); cube.data.materials.append(original)
        # The unselected instance must not be changed by assigning the selected cube.
        instance=bpy.data.objects.new('Unselected Instance',cube.data); bpy.context.collection.objects.link(instance)
        instance.select_set(False)
        for layer in list(cube.data.uv_layers): cube.data.uv_layers.remove(layer)
        def make_job():
            return {'id':uuid.uuid4().hex,'session':addon.SESSION,'expires':time.time()+30,
                    'revision':addon.snapshot()['revision'],'material':manifest,'options':options}
        def perform(job):
            result=bpy.ops.surface_studio.apply_material('EXEC_DEFAULT', True, payload=json.dumps(job))
            check(result=={'FINISHED'},'operator finishes: '+str(len(checks)))
            return addon.APPLY_RESULT
        result=perform(make_job())
        check(result['status']=='success','object assignment succeeds')
        check(result['autoUV']==1 and bool(cube.data.uv_layers),'missing UV generated')
        check(cube.data is not instance.data,'shared mesh isolated')
        check(len(instance.data.materials)==1 and instance.data.materials[0]==original,'unselected linked instance preserved')
        material=cube.active_material
        check(all(cube.data.materials[p.material_index]==material for p in cube.data.polygons),'all object faces assigned')
        check(cube.data.materials[0]==original,'original material slot preserved')
        nodes=material.node_tree.nodes
        check(nodes['Albedo'].image.colorspace_settings.name=='sRGB','albedo uses sRGB')
        check(all(nodes[c].image.colorspace_settings.name=='Non-Color' for c in ['Normal','Roughness','AO','Displacement']),'data maps use Non-Color')
        check(nodes['Principled BSDF'].inputs['Normal'].is_linked,'normal and bump connected')
        check(nodes['Principled BSDF'].inputs['Roughness'].is_linked,'roughness connected')
        check(nodes['Principled BSDF'].inputs['Base Color'].is_linked,'base color / AO connected')
        check(tuple(nodes['Mapping'].inputs['Scale'].default_value)==(2,2,2),'tiling scale respected')
        count=len(bpy.data.materials)
        perform(make_job())
        check(len(bpy.data.materials)==count,'same material and options reused')
        # A stale job must never alter a different selection.
        stale=make_job(); instance.select_set(True)
        before=instance.active_material
        try: addon.validate_job(stale); raise AssertionError('stale job accepted')
        except ValueError: checks.append('selection changes rejected')
        check(instance.active_material==before,'stale job does not modify target')
        instance.select_set(False)
        # Editing: only one selected face changes, other face assignments survive.
        for polygon in cube.data.polygons: polygon.material_index=0
        bpy.ops.object.mode_set(mode='EDIT')
        bm=bmesh.from_edit_mesh(cube.data); bm.faces.ensure_lookup_table()
        for face in bm.faces: face.select_set(False)
        bm.faces[0].select_set(True)
        bmesh.update_edit_mesh(cube.data)
        result=perform(make_job())
        bm=bmesh.from_edit_mesh(cube.data); bm.faces.ensure_lookup_table()
        check(result['faces']==1,'edit-mode selected face count')
        check(bm.faces[0].material_index!=0 and all(f.material_index==0 for f in list(bm.faces)[1:]),'unselected faces preserved')
        bpy.ops.object.mode_set(mode='OBJECT')
        # Main-thread timer: consume one declarative job and publish an acknowledged result.
        addon.MAILBOX=root/'mailbox'
        for name in ['sessions','requests','results']: (addon.MAILBOX/name).mkdir(parents=True)
        addon.CONNECTED=True
        job=make_job()
        addon.atomic_json(addon.MAILBOX/'requests'/(addon.SESSION+'.json'),job)
        addon.tick()
        ack=addon.read_json(addon.MAILBOX/'results'/(job['id']+'.json'))
        check(ack['status']=='success','mailbox request consumed and acknowledged')
        check(not (addon.MAILBOX/'requests'/(addon.SESSION+'.json')).exists(),'request consumed only once')
        # Undo is tested separately to avoid keeping invalidated RNA pointers.
        bpy.ops.ed.undo_push(message='Surface Studio test baseline')
        options['repeat']=3
        name=cube.name
        prior_material=cube.active_material.name
        perform(make_job())
        assigned=bpy.data.objects[name].active_material.name
        check(assigned!=prior_material,'changed options create separate material')
        bpy.ops.ed.undo()
        check(bpy.data.objects[name].active_material.name==prior_material,'Ctrl Z restores previous material')
        addon.unregister()
    report={'version':bpy.app.version_string,'passed':len(checks),'checks':checks}
    if '--' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--')+1]); output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SURFACE_TEST_PASS '+json.dumps(report,ensure_ascii=False),flush=True)

main()
