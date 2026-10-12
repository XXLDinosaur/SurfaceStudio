"""Foreground factory-scene raycast test. Quits its own Blender after reporting.
blender --factory-startup --python test_blender_viewport_drop.py -- report.json
"""
import json
import math
from pathlib import Path
import sys

import addon_utils
import bpy
from bpy_extras import view3d_utils
from mathutils import Quaternion

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'blender_addon'))
addon=addon_utils.enable('surface_studio_bridge',default_set=True)
report=Path(sys.argv[sys.argv.index('--')+1])
left=bpy.data.objects['Cube'];left.name='Raycast Target'
bpy.ops.mesh.primitive_cube_add(location=(3.5,0,0));right=bpy.context.object;right.name='Raycast Neighbor'
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
rv3d=area.spaces.active.region_3d
rv3d.view_rotation=Quaternion((1,0,0),math.pi/2)
rv3d.view_distance=12;rv3d.view_location=(1.5,0,0);rv3d.view_perspective='ORTHO'


def test():
    try:
        with bpy.context.temp_override(area=area,region=region):
            for obj in [left,right]:
                position=view3d_utils.location_3d_to_region_2d(region,rv3d,obj.location)
                actual=addon.mesh_at_drop(bpy.context,region.x+position.x,region.y+position.y)
                assert actual==obj, (obj.name,actual.name if actual else None)
            assert addon.mesh_at_drop(bpy.context,region.x+5,region.y+5) is None
            right.hide_select=True
            position=view3d_utils.location_3d_to_region_2d(region,rv3d,right.location)
            assert addon.mesh_at_drop(bpy.context,region.x+position.x,region.y+position.y) is None
        report.write_text(json.dumps({'ok':True,'version':bpy.app.version_string,'checks':['left target','right target','empty space','locked mesh']}),encoding='utf-8')
    except Exception as exc:
        report.write_text(json.dumps({'ok':False,'error':str(exc)}),encoding='utf-8')
    finally:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(test,first_interval=3)
