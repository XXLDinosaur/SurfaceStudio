"""Run in Blender --background --factory-startup --python test_blender_drag.py."""
import json
import sys
import tempfile
import time
from pathlib import Path

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'blender_addon'))
addon = addon_utils.enable('surface_studio_bridge', default_set=True)


def main():
    with tempfile.TemporaryDirectory(prefix='surface-drop-test-') as directory:
        root = Path(directory); maps = root/'maps'; maps.mkdir()
        exe = root/'Surface Studio.exe'; exe.write_bytes(b'test marker')
        bpy.context.preferences.addons['surface_studio_bridge'].preferences.executable_path = str(exe)
        image = bpy.data.images.new('Drop Test', width=8, height=8)
        image.generated_color = (.7,.05,.01,1); image.filepath_raw=str(maps/'color.png'); image.file_format='PNG'; image.save()
        bpy.data.images.remove(image)
        target = bpy.data.objects['Cube']; target.name='Drop Target'
        other = target.copy(); other.data=target.data; other.name='Selected Other'; bpy.context.scene.collection.objects.link(other)
        for obj in bpy.context.selected_objects: obj.select_set(False)
        other.select_set(True); bpy.context.view_layer.objects.active=other
        before_data=other.data; before_slots=list(other.data.materials)
        manifest={'id':'fixture','name':'Drop Fixture','assetId':'fixture','root':str(root),'folder':'maps',
                  'maps':[{'channel':'Albedo','path':str(maps/'color.png'),'name':'color.png','ext':'PNG'}]}
        job={'material':manifest,'options':{'repeat':1,'autoUV':True},'app':'SurfaceStudio','protocol':1,
             'id':'a'*32,'created':time.time(),'expires':time.time()+300}
        drops=root/'data/blender/drops'; drops.mkdir(parents=True)
        path=drops/('a'*32+'.ssmat');path.write_text(json.dumps(job))
        assert addon.read_drop(path)[1]['id']==job['id']
        selection=[obj.name for obj in bpy.context.selected_objects]
        def drop(name):
            area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
            region=next(r for r in area.regions if r.type=='WINDOW')
            with bpy.context.temp_override(area=area,region=region):
                return bpy.ops.surface_studio.drop_material('EXEC_DEFAULT', True, filepath=str(path),target_name=name)
        bpy.ops.ed.undo_push(message='Before material drop')
        assert drop(target.name)=={'FINISHED'}
        target=bpy.data.objects['Drop Target'];other=bpy.data.objects['Selected Other']
        assert target.active_material and target.active_material.name.startswith('SS · ')
        assert other.data==before_data and list(other.data.materials)==before_slots
        assert [obj.name for obj in bpy.context.selected_objects]==selection
        assert bpy.context.view_layer.objects.active==other
        assert addon.read_json(root/'data/blender/results'/('a'*32+'.json'))['status']=='success'
        count=len(bpy.data.materials)
        assert drop(target.name)=={'CANCELLED'}
        assert len(bpy.data.materials)==count
        bpy.ops.ed.undo()
        target=bpy.data.objects['Drop Target'];other=bpy.data.objects['Selected Other']
        assert list(target.data.materials)==list(other.data.materials)
        job['id']='b'*32;path=drops/('b'*32+'.ssmat');path.write_text(json.dumps(job))
        assert drop('')=={'CANCELLED'}
        assert addon.read_json(root/'data/blender/results'/('b'*32+'.json'))['status']=='error'
        job['expires']=time.time()-1;path.write_text(json.dumps(job))
        try: addon.read_drop(path);raise AssertionError('Expired drop accepted')
        except ValueError: pass
        assert bpy.types.SURFACESTUDIO_FH_material.bl_file_extensions=='.ssmat'
        print('DROP_TEST_PASS '+bpy.app.version_string+': target-only, linked mesh isolation, selection preservation, undo, duplicate guard, empty drop and expiry',flush=True)
    addon_utils.disable('surface_studio_bridge', default_set=True)


main()
