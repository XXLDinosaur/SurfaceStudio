"""Run in isolated Blender factory startup; no user scene or preferences are touched."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import bpy

BASE = Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'blender_addon'))
import surface_studio_bridge as addon
from surface_studio_bridge.native_material import export_snapshot


def main():
    addon.register()
    with tempfile.TemporaryDirectory(prefix='ss-native-material-') as temporary:
        root = Path(temporary)
        source = root/'source'; source.mkdir()
        library = root/'我的材质库'; library.mkdir()
        material = bpy.data.materials.new('自制 水面'); material.use_nodes=True
        original_image = bpy.data.images.new('Generated live edit',width=8,height=8)
        original_image.generated_color=(.7,.2,.1,1)
        original_image.filepath_raw=str(source/'original.png'); original_image.file_format='PNG'; original_image.save()
        original_image.pixels[0]=.123
        expected_pixel=original_image.pixels[0]
        group = bpy.data.node_groups.new('Custom nested texture','ShaderNodeTree')
        group.interface.new_socket(name='Color',in_out='OUTPUT',socket_type='NodeSocketColor')
        image_node=group.nodes.new('ShaderNodeTexImage');image_node.image=original_image
        output=group.nodes.new('NodeGroupOutput');group.links.new(image_node.outputs['Color'],output.inputs['Color'])
        node=material.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=group
        shader=material.node_tree.nodes.get('Principled BSDF');material.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
        shader.inputs['Roughness'].default_value=.234
        counts=(len(bpy.data.materials),len(bpy.data.images),len(bpy.data.node_groups))
        stage,final=export_snapshot(material,str(library),'自制 水面')
        assert counts==(len(bpy.data.materials),len(bpy.data.images),len(bpy.data.node_groups))
        assert image_node.image==original_image and node.node_tree==group and original_image.packed_file is None
        assert original_image.pixels[0]==expected_pixel,(original_image.pixels[0],expected_pixel)
        saved=json.loads((stage/'surface-material.json').read_text(encoding='utf-8'))
        # Delete the source image before preview and import: packed assets must stand alone.
        (source/'original.png').unlink()
        completed=subprocess.run([bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec',
            '--threads','4','--python-exit-code','1','--python',str(BASE/'blender_addon/surface_studio_bridge/preview_worker.py'),
            '--',str(stage)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        assert completed.returncode==0,completed.stdout.decode(errors='replace')[-2500:]
        assert (stage/'preview.png').stat().st_size>1000
        stage.rename(final)
        moved=root/'重装后材质库'; library.rename(moved); final=moved/final.name
        manifest={'kind':'blend','root':str(moved),'folder':final.name,'name':'自制 水面','id':'test-native',
            'assetId':saved['id'],'maps':[], 'native':{'path':str(final/'material.blend'),
                'materialName':saved['materialName'],'blenderVersion':saved['blenderVersion']}}
        loaded,warnings=addon.build_material(manifest,{'repeat':7,'flipNormalY':True})
        assert abs(loaded.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value-.234)<.0001
        loaded_group=next(n.node_tree for n in loaded.node_tree.nodes if n.type=='GROUP')
        loaded_image=next(n.image for n in loaded_group.nodes if n.type=='TEX_IMAGE')
        assert loaded_image.packed_file and abs(loaded_image.pixels[0]-expected_pixel)<.01,loaded_image.pixels[0]
        bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object
        job={'material':manifest,'options':{'autoUV':True}}
        result=addon.apply_job(bpy.context,job,target=obj)
        assert result['status']=='success' and obj.active_material
        assert any(n.type=='GROUP' for n in obj.active_material.node_tree.nodes)
        # A reinstalled SS can derive the identity and all paths from the package alone.
        assert (final/'surface-material.json').exists() and saved['id']
        bad=material.node_tree.nodes.new('ShaderNodeTexCoord');bad.object=obj
        try: export_snapshot(material,str(moved),'Object-dependent')
        except ValueError as exc: assert '依赖' in str(exc)
        else: raise AssertionError('Object dependency was accepted')
        print('SS_NATIVE_ROUNDTRIP_OK '+bpy.app.version_string,flush=True)
    addon.unregister()


if __name__=='__main__': main()
