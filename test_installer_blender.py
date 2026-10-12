"""Usage: python test_installer_blender.py /path/to/blender.exe [...]
All config/scripts/datafiles are redirected to a temporary test profile.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

import installer_core as core

ROOT = Path(__file__).resolve().parent


def test(executable):
    with tempfile.TemporaryDirectory(prefix='ss-install-test-') as directory:
        root = Path(directory)
        env = dict(os.environ)
        for name, suffix in [('CONFIG', 'config'), ('SCRIPTS', 'scripts'), ('DATAFILES', 'datafiles'), ('EXTENSIONS', 'extensions')]:
            (root/suffix).mkdir()
            env['BLENDER_USER_'+name] = str(root/suffix)
        info = core.probe(executable, ROOT/'installer_blender.py', env)
        assert Path(info['config']).resolve().is_relative_to(root.resolve()), info
        assert Path(info['scripts']).resolve().is_relative_to(root.resolve()), info
        seed = root/'seed.py'
        seed.write_text("import bpy\nbpy.context.preferences.view.show_splash = False\nbpy.context.preferences.inputs.use_zoom_to_mouse = True\nbpy.context.preferences.filepaths.use_scripts_auto_execute = True\nbpy.ops.wm.save_userpref()\n", encoding='utf-8')
        assert core.run([executable, '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(seed)], env=env).returncode == 0
        exe = root/'中文 安装位置/Surface Studio.exe'; exe.parent.mkdir(); exe.write_bytes(b'test-path')
        first = core.install_blender(info, exe, ROOT/'surface_studio_bridge.zip', ROOT/'installer_blender.py', root/'backups', env, check_running=False)
        assert first['ok']
        # Repair/update and path changes must persist on a second fresh process.
        moved = root/'另一个位置/Surface Studio.exe'; moved.parent.mkdir(); moved.write_bytes(b'new-path')
        second = core.install_blender(info, moved, ROOT/'surface_studio_bridge.zip', ROOT/'installer_blender.py', root/'backups', env, check_running=False)
        assert second['ok'] and second['configured_path'] == str(moved)
        check = root/'check.py'
        check.write_text("import bpy\nassert not bpy.context.preferences.view.show_splash\nassert bpy.context.preferences.inputs.use_zoom_to_mouse\nassert bpy.context.preferences.filepaths.use_scripts_auto_execute\n", encoding='utf-8')
        result = core.run([executable, '--background', '--python-exit-code', '1', '--python', str(check)], env=env)
        assert result.returncode == 0, result.stdout+result.stderr
        prefs = root/'config/userpref.blend'; old = prefs.read_bytes()
        addon = root/'scripts/addons/surface_studio_bridge/__init__.py'; old_addon = addon.read_bytes()
        corrupt = root/'broken.zip'
        with zipfile.ZipFile(corrupt, 'w') as z: z.writestr('surface_studio_bridge/__init__.py', "raise RuntimeError('test broken plugin')")
        try:
            core.install_blender(info, exe, corrupt, ROOT/'installer_blender.py', root/'backups', env, check_running=False)
            raise AssertionError('Broken plugin must fail')
        except RuntimeError: pass
        assert prefs.read_bytes() == old and addon.read_bytes() == old_addon
        core.worker(executable, 'verify', ROOT/'installer_blender.py', {'ss_exe': str(moved)}, env)
        # Existing PBR behavior also needs to work on every advertised minor series.
        result = core.run([executable, '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(ROOT/'test_blender.py')], env=env)
        assert result.returncode == 0, result.stdout[-2000:]+result.stderr[-1000:]
        print(json.dumps({'version': info['version_string'], 'install': 'passed', 'restart': 'passed',
                          'repair': 'passed', 'existing_preferences': 'preserved', 'rollback': 'passed', 'PBR': 'passed'}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) < 2: raise SystemExit('Pass one or more Blender executable paths')
    for executable in sys.argv[1:]: test(executable)
