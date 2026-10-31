"""SketchUp per-user extension discovery and installation on Windows."""
import os
import shutil
import tempfile
import winreg
from pathlib import Path
from zipfile import ZipFile

MEMBERS = ('ss_surface_studio.rb', 'ss_surface_studio/bridge.rb', 'ss_surface_studio/dialog.js')


def installations():
    key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as parent:
                    for i in range(winreg.QueryInfoKey(parent)[0]):
                        try:
                            with winreg.OpenKey(parent, winreg.EnumKey(parent, i)) as child:
                                name = winreg.QueryValueEx(child, 'DisplayName')[0]
                                location = winreg.QueryValueEx(child, 'InstallLocation')[0]
                                if location:
                                    yield name, Path(location.strip('"'))
                        except OSError:
                            continue
            except OSError:
                continue


def discover(entries=None):
    found = {}
    for name, location in installations() if entries is None else entries:
        if name not in ('SketchUp 2025', 'SketchUp 2026'):
            continue
        for exe in (location/'SketchUp.exe', location/'SketchUp/SketchUp.exe'):
            if exe.is_file():
                found[name] = dict(host='SketchUp', path=str(exe.resolve()), version_string=name[-4:],
                                   supported=True, reason='安装当前用户的 SS 连接插件')
                break
    return list(found.values())


def install(info, archive, backup_root, appdata=None):
    year = info['version_string']
    if year not in ('2025', '2026') or not Path(info['path']).is_file():
        raise ValueError('请重新检测 SketchUp 安装位置')
    target = Path(appdata or os.environ['APPDATA'])/'SketchUp'/('SketchUp '+year)/'SketchUp/Plugins'
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='sketchup-'+year+'-', dir=backup_root))
    with ZipFile(archive) as bundle:
        contents = {name: bundle.read(name) for name in MEMBERS}
    for name in MEMBERS:
        old = target/name
        if old.is_file():
            (backup/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, backup/name)
    try:
        for name, data in contents.items():
            dest = target/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if dest.read_bytes() != data:
                raise OSError('插件文件校验失败')
    except Exception:
        for name in MEMBERS:
            if (backup/name).exists():
                shutil.copy2(backup/name, target/name)
            else:
                (target/name).unlink(missing_ok=True)
        raise
