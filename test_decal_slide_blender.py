"""Factory-scene regression for moving decals around a sphere."""
import bpy, sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent/'blender_addon'))
from surface_studio_bridge.decal import place, SURFACESTUDIO_OT_attach_decal

def material(*args):
    mat=bpy.data.materials.new('test');mat.use_nodes=True
    mask=mat.node_tree.nodes.new('ShaderNodeRGB');mask.name='Opacity'
    return mat, []

bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,radius=2)
target=bpy.context.object
place(bpy.context,target,Vector((0,0,2)),Vector((0,0,1)),{'name':'test','maps':[{'channel':'Opacity'}]},material,{})
decal=bpy.context.object
from surface_studio_bridge.decal import SurfaceSlide, SURFACESTUDIO_OT_slide_decal
from types import SimpleNamespace
bpy.context.view_layer.update()
slide=SurfaceSlide(target,bpy.context.evaluated_depsgraph_get(),decal.matrix_world)
previous=None
for step in range(121):
    x=-1.5+step*.025
    world=slide.move(Vector((x,0,6)),Vector((0,0,-1)))
    assert world is not None
    if previous is not None:
        assert (world.translation-previous.translation).length<.06
        assert world.to_quaternion().rotation_difference(previous.to_quaternion()).angle<.06
    previous=world
before=slide.world.copy()
assert slide.move(Vector((5,0,6)),Vector((0,0,-1))) is None
assert slide.world==before
# Exercise the actual modal invoke/cancel/confirm paths without a user scene.
area=SimpleNamespace(type='VIEW_3D',header_text_set=lambda value:None)
context=SimpleNamespace(object=decal,mode='OBJECT',area=area,region=SimpleNamespace(type='WINDOW'),
    evaluated_depsgraph_get=bpy.context.evaluated_depsgraph_get,
    window_manager=SimpleNamespace(modal_handler_add=lambda op:None))
assert SURFACESTUDIO_OT_slide_decal.poll(context)
context.object=target
assert not SURFACESTUDIO_OT_slide_decal.poll(context)
context.object=decal
original=decal.matrix_basis.copy();muted=decal.constraints[0].mute
op=SimpleNamespace(report=lambda *args:None)
op.restore=lambda:SURFACESTUDIO_OT_slide_decal.restore(op)
assert SURFACESTUDIO_OT_slide_decal.invoke(op,context,None)=={'RUNNING_MODAL'}
world=op.slide.move(Vector((1,0,6)),Vector((0,0,-1)))
decal.matrix_world=world;op.changed=True
assert SURFACESTUDIO_OT_slide_decal.modal(op,context,SimpleNamespace(type='ESC'))=={'CANCELLED'}
assert all(abs(original[i][j]-decal.matrix_basis[i][j])<1e-5 for i in range(4) for j in range(4))
assert decal.constraints[0].mute==muted
assert SURFACESTUDIO_OT_slide_decal.invoke(op,context,None)=={'RUNNING_MODAL'}
world=op.slide.move(Vector((1,0,6)),Vector((0,0,-1)))
decal.matrix_world=world;op.changed=True
assert SURFACESTUDIO_OT_slide_decal.modal(op,context,SimpleNamespace(type='RET',value='PRESS'))=={'FINISHED'}
bpy.context.view_layer.update()
assert (decal.matrix_world.translation-world.translation).length<1e-5
assert decal.constraints[0].mute
print('DECAL_SLIDE_PASS continuous position/frame, missed ray, cancel, confirm, poll',flush=True)
