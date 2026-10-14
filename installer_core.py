"""Surface Studio per-user installation and transactional Blender setup."""
import concurrent.futures
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
MODULE = 'surface_studio_bridge'
# Each minor series is verified by the installer integration tests.
SUPPORTED = {(4, 2), (4, 3), (5, 1), (5, 2)}
SPAWN_LOCK = threading.Lock()


def spawn(command, env=None, **kwargs):
    child_env = dict(os.environ if env is None else env)
    child_env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    bundle = getattr(sys, '_MEIPASS', None)
    if bundle:
        child_env['PATH'] = os.pathsep.join(p for p in child_env.get('PATH', '').split(os.pathsep)
                                          if not os.path.normcase(p).startswith(os.path.normcase(str(bundle))))
    with SPAWN_LOCK:
        # A frozen setup must not make Blender load setup's bundled DLLs.
        reset = os.name == 'nt' and bundle
        if reset: ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            return subprocess.Popen(command, env=child_env, creationflags=NO_WINDOW, **kwargs)
        finally:
            if reset: ctypes.windll.kernel32.SetDllDirectoryW(str(bundle))


def run(command, timeout=90, env=None):
    with spawn(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
               text=True, encoding='utf-8', errors='replace') as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def processes():
    """Read process paths without stopping any user's application."""
    if os.name != 'nt':
        return []
    result = run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                  "Get-CimInstance Win32_Process -Filter \"Name = 'blender.exe' OR Name = 'Surface Studio.exe'\" | Select-Object Name,ExecutablePath,ProcessId | ConvertTo-Json -Compress"], timeout=20)
    if result.returncode:
        raise RuntimeError('无法检查运行中的程序，请重试')
    items = json.loads(result.stdout or '[]')
    return items if isinstance(items, list) else [items]


def candidate_paths():
    candidates = set()
    def add(path):
        p = Path(path)
        if p.is_file() and p.name.lower() == 'blender.exe':
            candidates.add(str(p.resolve()))
    if os.name == 'nt':
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for key in [r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                        r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall']:
                try:
                    with winreg.OpenKey(hive, key) as parent:
                        for i in range(winreg.QueryInfoKey(parent)[0]):
                            try:
                                with winreg.OpenKey(parent, winreg.EnumKey(parent, i)) as child:
                                    name = winreg.QueryValueEx(child, 'DisplayName')[0]
                                    if 'blender' not in name.lower(): continue
                                    for field in ['InstallLocation', 'DisplayIcon']:
                                        try:
                                            value = winreg.QueryValueEx(child, field)[0].strip('"')
                                            if field == 'DisplayIcon': value = re.sub(r',-?\d+$', '', value).strip('"')
                                            add(Path(value) / 'blender.exe' if field == 'InstallLocation' else value)
                                        except OSError: pass
                            except OSError: pass
                except OSError: pass
    roots = [Path(os.environ.get('ProgramFiles', r'C:\Program Files')),
             Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs']
    if os.name == 'nt':
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for n in range(26):
            drive = f'{chr(65+n)}:\\'
            if mask & (1 << n) and ctypes.windll.kernel32.GetDriveTypeW(drive) == 3:
                roots.extend([Path(drive)/'Program Files', Path(drive)/'Program Files (x86)'])
    for root in roots:
        for parent in [root/'Blender Foundation', root/'Blender', root/'Steam/steamapps/common']:
            if not parent.is_dir(): continue
            add(parent/'blender.exe')
            try:
                for child in parent.iterdir():
                    if child.is_dir() and 'blender' in child.name.lower(): add(child/'blender.exe')
            except OSError: pass
    on_path = shutil.which('blender.exe')
    if on_path: add(on_path)
    for proc in processes():
        if proc.get('ExecutablePath'): add(proc['ExecutablePath'])
    return sorted(candidates)


def worker(executable, mode, script, values=None, env=None):
    with tempfile.TemporaryDirectory(prefix='surface-blender-') as directory:
        job_path = Path(directory)/'job.json'
        result_path = Path(directory)/'result.json'
        job_path.write_text(json.dumps({'mode': mode, 'result': str(result_path), **(values or {})}), encoding='utf-8')
        command = [str(executable), '--background', '--disable-autoexec']
        if mode == 'probe': command += ['--factory-startup']
        command += ['--python-exit-code', '1', '--python', str(script), '--', str(job_path)]
        completed = run(command, env=env)
        data = json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {}
        if completed.returncode or not data.get('ok'):
            raise RuntimeError(data.get('error') or ('Blender 执行失败：' + completed.stdout[-1000:] + completed.stderr[-500:]))
        return data


def probe(executable, script, env=None):
    p = Path(executable).resolve()
    if not p.is_file() or p.name.lower() != 'blender.exe':
        raise ValueError('请选择 Blender 安装目录里的 blender.exe')
    data = worker(p, 'probe', script, env=env)
    data['path'] = str(p)
    data['supported'] = tuple(data['version'][:2]) in SUPPORTED and data['cycle'] == 'release'
    data['reason'] = '兼容 · 将安装并启用连接插件' if data['supported'] else '此版本尚未验证，暂不自动安装'
    return data


def discover(script):
    paths = candidate_paths()
    def inspect(path):
        try: return probe(path, script)
        except Exception as exc: return {'path': path, 'supported': False, 'version_string': '检测失败', 'reason': str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(inspect, paths))


def restore_blender(snapshot):
    """Restore only the exact addon/config files recorded by our transaction."""
    target = Path(snapshot['target'])
    backup = Path(snapshot['backup'])
    config = Path(snapshot['config'])
    if target.name != MODULE or target.parent.name != 'addons':
        raise RuntimeError('拒绝恢复非 SS 插件目录')
    if target.is_symlink(): raise RuntimeError('插件目录是链接，请手动处理')
    if target.exists(): shutil.rmtree(target)
    if snapshot['had_addon']: shutil.copytree(backup/'addon', target)
    # Blender may create numbered preference backups while saving.
    for item in config.glob('userpref.blend*'):
        if item.is_file(): item.unlink()
    for item in (backup/'preferences').iterdir(): shutil.copy2(item, config/item.name)


def install_blender(info, ss_exe, addon_zip, script, backup_root, env=None, check_running=True):
    if check_running and any(p['Name'].lower() == 'blender.exe' for p in processes()):
        raise RuntimeError('请先关闭所有 Blender 窗口，再点击重试安装；SS 软件可以独立使用')
    current = probe(info['path'], script, env=env)
    if not current['supported']: raise RuntimeError(current['reason'])
    target = Path(current['scripts'])/'addons'/MODULE
    config = Path(current['config']).resolve()
    if not current['scripts'] or not current['config']: raise RuntimeError('无法确定 Blender 用户配置位置')
    if target.name != MODULE or target.parent.name != 'addons' or target.is_symlink() or getattr(target, 'is_junction', lambda: False)():
        raise RuntimeError('无效的 Blender 插件目录')
    target = target.resolve()
    backup = Path(backup_root)/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    backup.mkdir(parents=True)
    (backup/'preferences').mkdir()
    if target.exists(): shutil.copytree(target, backup/'addon')
    config.mkdir(parents=True, exist_ok=True)
    for item in config.glob('userpref.blend*'):
        if item.is_file(): shutil.copy2(item, backup/'preferences'/item.name)
    snapshot = {'target': str(target), 'config': str(config), 'backup': str(backup), 'had_addon': target.exists()}
    (backup/'restore.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    values = {'ss_exe': str(Path(ss_exe).resolve()), 'addon_zip': str(Path(addon_zip).resolve()),
              'addon_target': str(target), 'config': str(config)}
    try:
        worker(current['path'], 'install', script, values, env)
        verified = worker(current['path'], 'verify', script, values, env)
        return {'ok': True, 'path': current['path'], 'version': current['version_string'],
                'backup': str(backup), 'configured_path': verified['configured_path']}
    except Exception:
        restore_blender(snapshot)
        raise


def install_application(payload, destination):
    payload, destination = Path(payload), Path(destination).expanduser()
    if not destination.is_absolute() or destination.parent == destination:
        raise ValueError('请选择独立的软件文件夹，不要选择磁盘根目录')
    destination = destination.resolve()
    executable = destination/'Surface Studio.exe'
    for proc in processes():
        if proc.get('ExecutablePath') and Path(proc['ExecutablePath']).resolve() == executable:
            raise RuntimeError('此位置的 SS 仍在运行，请退出 Surface Studio.exe 后台进程后重试')
    source = payload/'Surface Studio.exe'
    if not source.is_file(): raise RuntimeError('安装包缺少 SS 程序')
    destination.mkdir(parents=True, exist_ok=True)
    if executable.exists():
        backup = destination/'data/installer-backups'/('app-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        backup.mkdir(parents=True)
        shutil.copy2(executable, backup/executable.name)
    with tempfile.NamedTemporaryFile(dir=destination, suffix='.installing', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        shutil.copyfile(source, temporary)
        if hashlib.sha256(temporary.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
            raise RuntimeError('程序复制校验失败')
        os.replace(temporary, executable)
    finally:
        temporary.unlink(missing_ok=True)
    for name in ['安装与使用说明.txt', 'surface_studio_bridge.zip', 'LICENSE']:
        if (payload/name).is_file(): shutil.copy2(payload/name, destination/name)
    return executable


def create_shortcuts(executable):
    """Per-user Start menu entry; never requires administrator rights."""
    executable = Path(executable).resolve()
    folder = Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Surface Studio'
    folder.mkdir(parents=True, exist_ok=True)
    # Pass literal values as JSON file data, not PowerShell command interpolation.
    with tempfile.TemporaryDirectory() as directory:
        data = Path(directory)/'shortcut.json'
        data.write_text(json.dumps({'exe': str(executable), 'link': str(folder/'Surface Studio.lnk')}), encoding='utf-8-sig')
        script = Path(directory)/'shortcut.ps1'
        script.write_text("param([string]$DataPath)\n$d=Get-Content -LiteralPath $DataPath -Raw | ConvertFrom-Json\n$s=(New-Object -ComObject WScript.Shell).CreateShortcut($d.link)\n$s.TargetPath=$d.exe\n$s.WorkingDirectory=Split-Path -LiteralPath $d.exe\n$s.IconLocation=$d.exe\n$s.Save()\n", encoding='utf-8-sig')
        result = run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script), str(data)])
        if result.returncode: raise RuntimeError('开始菜单快捷方式创建失败：'+result.stderr[-500:])
