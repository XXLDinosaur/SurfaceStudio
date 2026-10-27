"""Isolated background Blender preview; no user's scene or preferences are loaded."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main(folder):
    meta = json.loads((folder/'surface-material.json').read_text(encoding='utf-8'))
    with bpy.data.libraries.load(str(folder/'material.blend'), link=False) as (source, target):
        target.materials = [meta['materialName']]
    material = target.materials[0]
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32)
    sphere = bpy.context.object; sphere.data.materials.append(material)
    for face in sphere.data.polygons: face.use_smooth = True
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 16
    scene.render.resolution_x = 512; scene.render.resolution_y = 512; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True; scene.render.filepath = str(folder/'preview.png')
    scene.world = bpy.data.worlds.new('SS preview world'); scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.35,.35,.35,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    bpy.ops.object.camera_add(location=(3,-5,2.4))
    camera = bpy.context.object; camera.rotation_euler = (-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 2.5; scene.camera = camera
    for location, energy, size in [((2,-3,4),700,4),((-3,-1,2),450,3),((1,3,3),850,2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        lamp = bpy.context.object; lamp.data.energy=energy; lamp.data.shape='DISK'; lamp.data.size=size
        lamp.rotation_euler = (-Vector(location)).to_track_quat('-Z','Y').to_euler()
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    folder = Path(sys.argv[sys.argv.index('--')+1]).resolve()
    try:
        main(folder)
    except Exception as exc:
        (folder/'preview-error.txt').write_text(str(exc),encoding='utf-8')
        raise
