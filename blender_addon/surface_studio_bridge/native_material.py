"""Portable static shader graphs, copied and packed without editing the source material."""
import json
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
import bpy

FORMAT = 'surface-studio-blender-material'


def check_tree(tree, seen=None):
    seen = set() if seen is None else seen
    if not tree or tree in seen:
        return
    seen.add(tree)
    if tree.animation_data:
        raise ValueError('暂不支持带动画或驱动的材质节点，请先制作静态副本')
    for node in tree.nodes:
        if node.bl_idname == 'ShaderNodeScript':
            raise ValueError('暂不支持 OSL 脚本节点')
        image = getattr(node, 'image', None)
        if image and image.source not in {'FILE', 'GENERATED'}:
            raise ValueError('暂不支持 UDIM、视频、序列或渲染结果贴图：' + image.name)
        for prop in node.bl_rna.properties:
            if prop.type != 'POINTER' or prop.identifier in {'rna_type', 'id_data', 'image', 'node_tree', 'parent'}:
                continue
            value = getattr(node, prop.identifier, None)
            if isinstance(value, bpy.types.ID):
                raise ValueError('材质依赖场景对象或外部数据，请先移除该依赖：' + node.name)
        check_tree(getattr(node, 'node_tree', None), seen)


def export_snapshot(material, directory, name):
    """Return a private staging folder and its final destination; caller finishes preview."""
    if not directory or not Path(directory).is_absolute():
        raise ValueError('请选择完整的材质存放目录')
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError('请先选择一个已存在的存放目录')
    if material.animation_data:
        raise ValueError('暂不支持带动画或驱动的材质，请先制作静态副本')
    check_tree(material.node_tree)
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError('材质名称需要为 1–100 个字符')
    uid = uuid.uuid4().hex
    slug = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')[:60] or 'Material'
    final = root/(slug+'_'+uid[:12])
    stage = Path(tempfile.mkdtemp(prefix='.ss-export-', dir=root))
    clone, groups, images, temporary_images = None, {}, {}, []
    try:
        clone = material.copy()
        for key in list(clone.keys()):
            if key.startswith('surface_studio_'): del clone[key]
        def copy_tree(tree):
            if not tree: return
            for node in tree.nodes:
                group = getattr(node, 'node_tree', None)
                if group:
                    if group not in groups:
                        groups[group] = group.copy()
                        copy_tree(groups[group])
                    node.node_tree = groups[group]
                source = getattr(node, 'image', None)
                if source:
                    if source not in images:
                        copied = source.copy(); images[source] = copied
                        # Blender's image.copy() does not copy unsaved pixel edits reliably.
                        # Copy the live pixel buffer explicitly before packing the private copy.
                        if source.is_dirty or source.source == 'GENERATED':
                            from array import array
                            pixels = array('f', [0.0]) * len(source.pixels)
                            source.pixels.foreach_get(pixels)
                            copied.pixels.foreach_set(pixels)
                            copied.update()
                            # Saving a private image makes dirty/generated pixels authoritative;
                            # packing a generated copy alone can reuse its old generated color.
                            temporary_image = stage/(uuid.uuid4().hex+('.exr' if source.is_float else '.png'))
                            copied.file_format = 'OPEN_EXR' if source.is_float else 'PNG'
                            copied.filepath_raw = str(temporary_image)
                            copied.save()
                            copied.source = 'FILE'
                            copied.pack(data=temporary_image.read_bytes(), data_len=temporary_image.stat().st_size)
                            temporary_images.append(temporary_image)
                        elif not source.packed_file and source.source == 'FILE':
                            path = Path(bpy.path.abspath(source.filepath, library=source.library))
                            if not path.is_file(): raise ValueError('贴图文件不存在：'+source.name)
                            copied.filepath = str(path)
                        if not copied.packed_file: copied.pack()
                        if not copied.packed_file: raise ValueError('无法打包贴图：'+source.name)
                    node.image = images[source]
        copy_tree(clone.node_tree)
        clone.asset_mark()
        bpy.data.libraries.write(str(stage/'material.blend'), {clone}, path_remap='RELATIVE_ALL', fake_user=True, compress=True)
        for path in temporary_images: path.unlink()
        meta = {'format':FORMAT, 'version':1, 'id':uid, 'name':name,
                'materialName':clone.name, 'blendFile':'material.blend', 'preview':'preview.png',
                'blenderVersion':list(bpy.app.version), 'created':time.time()}
        (stage/'surface-material.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        return stage, final
    except Exception:
        shutil.rmtree(stage)
        raise
    finally:
        if clone: bpy.data.materials.remove(clone)
        for group in reversed(list(groups.values())): bpy.data.node_groups.remove(group)
        for image in images.values(): bpy.data.images.remove(image)


def import_material(manifest):
    native = manifest.get('native', {})
    folder = (Path(manifest['root'])/manifest['folder']).resolve()
    path = Path(native.get('path','')).resolve()
    if not path.is_relative_to(folder) or path.name != 'material.blend' or not path.is_file():
        raise ValueError('Blender 材质包路径无效或文件缺失')
    version = native.get('blenderVersion', [])
    if not isinstance(version,list) or len(version)!=3 or not all(type(v) is int for v in version):
        raise ValueError('材质包的 Blender 版本无效')
    if tuple(version[:2]) > bpy.app.version[:2]:
        raise ValueError('该材质由更新版本 Blender 保存，请使用 Blender '+'.'.join(map(str,version[:2]))+' 或更高版本')
    name = native.get('materialName')
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        if name not in source.materials: raise ValueError('材质包内找不到指定材质')
        target.materials = [name]
    material = target.materials[0]
    if not material: raise ValueError('无法读取 Blender 材质')
    material.name = 'SS · '+manifest['name']
    return material, ['已保留原始节点；SS 的平铺、AO、法线翻转选项不改写此材质']
