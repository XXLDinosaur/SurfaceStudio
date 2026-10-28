"""Factory-scene regression for moving decals around a sphere."""
import bpy, sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent/'blender_addon'))
from surface_studio_bridge.decal import place, improve_surface, SURFACESTUDIO_OT_attach_decal

def material(*args):
    mat=bpy.data.materials.new('test');mat.use_nodes=True
    mask=mat.node_tree.nodes.new('ShaderNodeRGB');mask.name='Opacity'
    return mat, []

bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=2)
target=bpy.context.object
place(bpy.context,target,Vector((0,0,2)),Vector((0,0,1)),{'name':'test','maps':[{'channel':'Opacity'}]},material,{})
decal=bpy.context.object
improve_surface(decal);improve_surface(decal)
assert decal.modifiers[0].name=='SS Surface Detail'
# Sample triangle interiors, not just vertices: faces can cut through the target.
for position in [(0,0,2),(1.8,0,2)]:
    decal.location=position
    bpy.context.view_layer.update()
    evaluated=decal.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
    gaps=[]
    for tri in mesh.loop_triangles:
        vertices=[evaluated.matrix_world@mesh.vertices[i].co for i in tri.vertices]
        for weights in [(1/3,1/3,1/3),(.5,.5,0),(0,.5,.5),(.5,0,.5)]:
            point=sum((v*w for v,w in zip(vertices,weights)),Vector())
            hit,near,normal,_=target.closest_point_on_mesh(point)
            assert hit
            gaps.append((point-near).dot(normal))
    evaluated.to_mesh_clear()
    print('MIN_FACE_CLEARANCE',position,min(gaps),flush=True)
    assert min(gaps)>0, 'Decal faces intersect target'
print('DECAL_CLEARANCE_PASS',flush=True)
