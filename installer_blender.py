"""Executed by Blender, never by the installer's Python runtime."""
import json
import sys
from pathlib import Path

import bpy


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    job = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    result = Path(job['result'])
    try:
        info = {
            'version': list(bpy.app.version), 'version_string': bpy.app.version_string,
            'cycle': bpy.app.version_cycle,
            'config': bpy.utils.user_resource('CONFIG'),
            'scripts': bpy.utils.user_resource('SCRIPTS'),
        }
        if job['mode'] == 'install':
            import addon_utils
            import importlib
            import shutil
            import zipfile
            module = 'surface_studio_bridge'
            addons = Path(bpy.utils.user_resource('SCRIPTS', path='addons', create=True))
            target = addons / module
            if target.resolve() != Path(job['addon_target']).resolve():
                raise RuntimeError('Blender 插件目录发生变化，请重新检测')
            if Path(info['config']).resolve() != Path(job['config']).resolve():
                raise RuntimeError('Blender 配置目录发生变化，请重新检测')
            # Do not replace a duplicate package outside the selected user directory.
            previous = sys.modules.get(module)
            if previous and Path(previous.__file__).resolve().parent != target.resolve():
                raise RuntimeError('其他目录中存在同名插件，请先在 Blender 中移除旧插件')
            addon_utils.disable(module, default_set=True)
            if target.exists():
                shutil.rmtree(target)
            with zipfile.ZipFile(job['addon_zip']) as archive:
                for name in archive.namelist():
                    part = Path(name)
                    if part.is_absolute() or '..' in part.parts or part.parts[0] != module:
                        raise RuntimeError('插件安装包包含无效路径')
                archive.extractall(addons)
            sys.modules.pop(module, None)
            importlib.invalidate_caches()
            bpy.utils.refresh_script_paths()
            addon_utils.modules_refresh()
            enabled = addon_utils.enable(module, default_set=True, persistent=True)
            if enabled is None or module not in bpy.context.preferences.addons:
                raise RuntimeError('插件未能启用')
            if Path(enabled.__file__).resolve().parent != target.resolve():
                raise RuntimeError('Blender 加载了其他目录的同名插件')
            prefs = bpy.context.preferences.addons[module].preferences
            prefs.executable_path = job['ss_exe']
            if bpy.ops.wm.save_userpref() != {'FINISHED'}:
                raise RuntimeError('Blender 偏好设置保存失败')
            info['configured_path'] = prefs.executable_path
        elif job['mode'] == 'verify':
            prefs = bpy.context.preferences.addons.get('surface_studio_bridge')
            import addon_utils
            if prefs is None or not addon_utils.check('surface_studio_bridge')[1]:
                raise RuntimeError('重启验证：插件未自动启用')
            if Path(prefs.preferences.executable_path) != Path(job['ss_exe']):
                raise RuntimeError('重启验证：SS 程序路径未保存')
            info['configured_path'] = prefs.preferences.executable_path
        result.write_text(json.dumps({'ok': True, **info}), encoding='utf-8')
    except Exception as exc:
        result.write_text(json.dumps({'ok': False, 'error': str(exc)}), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
