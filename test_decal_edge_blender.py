import bpy,sys
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent/'blender_addon'))
from surface_studio_bridge.decal import SurfaceSlide
bpy.ops.mesh.primitive_cube_add()
target=bpy.context.object
bpy.context.view_layer.update()
slide=SurfaceSlide(target,bpy.context.evaluated_depsgraph_get(),Matrix.Translation((0,0,1)))
assert slide.move(Vector((.95,0,4)),Vector((0,0,-1))) is not None
before=slide.world.copy()
assert slide.move(Vector((4,0,.95)),Vector((-1,0,0))) is None, 'crossed sharp cube edge'
assert slide.world==before
assert slide.move(Vector((.9,0,4)),Vector((0,0,-1))) is not None
assert (slide.world.to_3x3()@Vector((0,0,1))).dot(Vector((0,0,1)))>.999
print('CUBE_EDGE_PASS')
