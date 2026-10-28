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
for position in [(0,0,2),(1.8,0,2),(3,0,.5),(2,0,-2)]:
    decal.location=position
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    evaluated=decal.evaluated_get(graph)
    points=[evaluated.matrix_world@v.co for v in evaluated.data.vertices]
    errors=[abs(p.length-2) for p in points]
    print('POSITION',position,'MAX_SURFACE_ERROR',max(errors),flush=True)
    assert max(errors)<.025, (position,max(errors))
    normal=(evaluated.matrix_world.to_3x3()@Vector((0,0,1))).normalized()
    assert normal.dot(evaluated.matrix_world.translation.normalized())>.98
# Upgrade an existing decal via the user-facing operator.
decal.constraints.remove(decal.constraints['SS Surface Attachment'])
bpy.utils.register_class(SURFACESTUDIO_OT_attach_decal)
assert bpy.ops.surface_studio.attach_decal()=={'FINISHED'}
assert len(decal.constraints)==1
assert bpy.ops.surface_studio.attach_decal()=={'FINISHED'}
assert len(decal.constraints)==1
# Parent transforms and non-uniform scale must not break surface attachment.
target.location=(4,-2,1);target.rotation_euler=(.3,.6,.2);target.scale=(1.3,.8,1.1)
bpy.context.view_layer.update()
graph=bpy.context.evaluated_depsgraph_get();evaluated=decal.evaluated_get(graph)
inverse=target.matrix_world.inverted()
for vertex in evaluated.data.vertices:
    point=evaluated.matrix_world@vertex.co
    hit,nearest,_,_=target.closest_point_on_mesh(inverse@point)
    assert hit and (point-target.matrix_world@nearest).length<.025
bpy.utils.unregister_class(SURFACESTUDIO_OT_attach_decal)
print('DECAL_MOVEMENT_PASS',bpy.app.version_string,flush=True)
