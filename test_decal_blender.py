"""Run in a factory Blender process; never use or save the user's scene."""
import sys,json,math,tempfile,time
from types import SimpleNamespace
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'blender_addon'))
import surface_studio_bridge as addon
from surface_studio_bridge.decal import place
addon.register()
fixtures=tempfile.TemporaryDirectory(prefix='ss-decal-')
fixture=Path(fixtures.name)
if '--real' in sys.argv:
    assets=json.loads((ROOT/'.ui-test/decal/assets.json').read_text(encoding='utf-8'))
    asset=next(a for a in assets if 'Crack' in a['folder'])
else:
    maps=[]
    for channel,color in [('Albedo',(.4,.1,.02,1)),('Opacity',(1,1,1,1)),('Normal',(.5,.5,1,1)),('Roughness',(.8,.8,.8,1))]:
        image=bpy.data.images.new(channel,width=8,height=8);image.generated_color=color
        image.filepath_raw=str(fixture/(channel+'.png'));image.file_format='PNG';image.save();bpy.data.images.remove(image)
        maps.append({'name':channel+'.png','channel':channel,'ext':'PNG'})
    asset={'id':'decal-test','assetId':'decal-test','name':'Test decal','kind':'decal','sourceRoot':str(fixture),'folder':'.','maps':maps}
manifest={**asset,'root':asset['sourceRoot'],'maps':[{**m,'path':str(Path(asset['sourceRoot'])/asset['folder']/m['name'])} for m in asset['maps']]}
target=bpy.data.objects['Cube'];target.rotation_euler=(.3,.2,.4);target.scale=(1.3,.8,1.1)
bpy.context.view_layer.update()
before_mesh=target.data;before_slots=list(target.data.materials)
location=target.matrix_world@Vector((0,0,1))
normal=(target.matrix_world.to_3x3().inverted().transposed()@Vector((0,0,1))).normalized()
addon.validate_job({'material':manifest,'options':{}},target)
result=place(bpy.context,target,location,normal,manifest,addon.build_material,{})
assert result['status']=='success'
decal=bpy.context.object
bpy.context.view_layer.update()
assert target.data==before_mesh and list(target.data.materials)==before_slots
assert decal.parent==target and decal['ss_decal']
assert (decal.matrix_world.translation-location).length<1e-5
assert len(decal.data.uv_layers)==1
graph=bpy.context.evaluated_depsgraph_get();evaluated=decal.evaluated_get(graph)
distances=[(decal.matrix_world@v.co-location).dot(normal) for v in evaluated.data.vertices]
assert min(distances)>0 and max(distances)<.01, (min(distances),max(distances))
shader=next(n for n in decal.active_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert shader.inputs['Alpha'].links[0].from_node.name=='SS Decal Opacity'
assert all(n.extension=='CLIP' for n in decal.active_material.node_tree.nodes if n.type=='TEX_IMAGE')
first=decal;first.active_material.node_tree.nodes['SS Decal Opacity'].inputs[1].default_value=.4
place(bpy.context,target,location+Vector((.1,0,0)),normal,manifest,addon.build_material,{})
second=bpy.context.object
assert first.active_material!=second.active_material
assert second.active_material.node_tree.nodes['SS Decal Opacity'].inputs[1].default_value==1
assert first.active_material.node_tree.nodes['SS Decal Opacity'].inputs[1].default_value<.41
# Shrinkwrap tracks Blender's interpolated surface normal. Verify that twisting
# the decal leaves that attachment normal unchanged, including on scaled targets.
bpy.context.view_layer.update()
attachment_normal=(second.matrix_world.to_3x3()@Vector((0,0,1))).normalized()
second.delta_rotation_euler.z=.6;bpy.context.view_layer.update()
assert (second.matrix_world.to_3x3()@Vector((0,0,1))).normalized().dot(attachment_normal)>.9999
bpy.data.objects.remove(second,do_unlink=True)
assert target.data==before_mesh and list(target.data.materials)==before_slots
try:
    addon.apply_job(bpy.context,{'material':manifest,'options':{}},target=target)
    raise AssertionError('Decal must not replace original material')
except ValueError:pass
with tempfile.TemporaryDirectory() as directory:
    temporary=Path(directory);exe=temporary/'Surface Studio.exe';exe.touch()
    addon.executable=lambda:exe
    drops=temporary/'data/blender/drops';drops.mkdir(parents=True)
    job={'app':'SurfaceStudio','protocol':2,'id':'d'*32,'expires':time.time()+300,'material':manifest,'options':{}}
    path=drops/(job['id']+'.ssmat');path.write_text(json.dumps(job))
    addon.mesh_at_drop=lambda *args,**kwargs:(target,location,normal)
    area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
    with bpy.context.temp_override(area=area,region=region):
        if bpy.app.background:
            operator=SimpleNamespace(filepath=str(path),report=lambda *args:None)
            operator.execute=lambda context:addon.SURFACESTUDIO_OT_drop.execute(operator,context)
            invoke=lambda:addon.SURFACESTUDIO_OT_drop.invoke(operator,bpy.context,SimpleNamespace(mouse_x=0,mouse_y=0))
        else:
            invoke=lambda:bpy.ops.surface_studio.drop_material('INVOKE_DEFAULT',True,filepath=str(path))
        assert invoke()=={'FINISHED'}
        assert invoke()=={'CANCELLED'}
    assert list(target.data.materials)==before_slots
    assert json.loads((temporary/'data/blender/results'/('d'*32+'.json')).read_text())['status']=='success'
class TEST_OT_decal(bpy.types.Operator):
    bl_idname='test.surface_decal';bl_label='Decal undo test';bl_options={'UNDO'}
    def execute(self,context):
        place(context,context.scene.objects['Cube'],location,normal,manifest,addon.build_material,{})
        return {'FINISHED'}
bpy.utils.register_class(TEST_OT_decal)
before_count=len(bpy.data.objects)
bpy.ops.ed.undo_push(message='Before decal');bpy.ops.test.surface_decal('EXEC_DEFAULT',True);assert len(bpy.data.objects)==before_count+1
bpy.ops.ed.undo();assert len(bpy.data.objects)==before_count
bpy.utils.unregister_class(TEST_OT_decal)
print('DECAL_PASS',bpy.app.version_string,'rotated/scaled target, UV, surface offset, alpha, independent opacity, local rotation, original material preserved',flush=True)
addon.unregister()
fixtures.cleanup()
