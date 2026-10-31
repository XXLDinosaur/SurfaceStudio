"""Graphical, per-user SS setup. Bundle with build_installer.ps1."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import installer_core as core
import installer_sketchup

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
UPDATE_ARGS = None
PAYLOAD = ROOT/'installer_payload' if getattr(sys, 'frozen', False) else ROOT/'dist/installer_payload'


class Setup:
    def __init__(self):
        self._window = None
        self._guard = threading.Lock()
        self._items = []
        self._status = {'busy': False, 'stage': '准备安装', 'results': [], 'installed': ''}

    def state(self):
        return {**self._status, 'items': list(self._items)}

    def defaults(self):
        destination = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'Programs/SurfaceStudio'
        if UPDATE_ARGS:
            from update_handoff import validate_destination
            destination,ready=validate_destination(UPDATE_ARGS.update_destination,UPDATE_ARGS.ready_file)
            ready.write_text(json.dumps({'ready':True}),encoding='utf-8')
        return {'destination': str(destination), 'ss_version': '1.7.0', 'addon_version': '1.3.1', 'updateMode':bool(UPDATE_ARGS)}

    def auto_update(self):
        if not UPDATE_ARGS:return {'error':'不是更新模式'}
        try:
            from update_handoff import validate_destination,wait_for_previous
            destination,_=validate_destination(UPDATE_ARGS.update_destination,UPDATE_ARGS.ready_file)
            self._status.update(busy=True,stage='正在等待旧版 SS 退出…')
            wait_for_previous([int(p) for p in UPDATE_ARGS.wait_pids.split(',')])
            self._status['busy']=False
            result=self.scan()
            if result.get('error'):return result
            return self.install(str(destination),[i['path'] for i in self._items if i.get('supported')])
        except Exception as exc:
            self._status.update(busy=False,stage='更新未完成')
            return {'error':str(exc)}

    def scan(self):
        if not self._guard.acquire(blocking=False): return {'error': '正在处理，请稍候'}
        try:
            self._status.update(busy=True, stage='正在检测 Blender 和 SketchUp…')
            self._items = core.discover(ROOT/'installer_blender.py') + installer_sketchup.discover()
            return {'items': self._items}
        except Exception as exc: return {'error': str(exc)}
        finally:
            self._status.update(busy=False, stage='检测完成')
            self._guard.release()

    def browse_blender(self):
        import webview
        chosen = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=('Blender (blender.exe)',))
        if not chosen: return {}
        if not self._guard.acquire(blocking=False): return {'error': '正在处理，请稍候'}
        try:
            self._status.update(busy=True, stage='正在检测所选 Blender…')
            info = core.probe(chosen[0], ROOT/'installer_blender.py')
            self._items = [x for x in self._items if x['path'] != info['path']] + [info]
            return {'items': self._items}
        except Exception as exc: return {'error': str(exc)}
        finally:
            self._status.update(busy=False, stage='检测完成')
            self._guard.release()

    def browse_destination(self):
        import webview
        chosen = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not chosen: return {}
        base = Path(chosen[0])
        return {'destination': str(base if (base/'Surface Studio.exe').exists() or base.name.lower() == 'surfacestudio' else base/'SurfaceStudio')}

    def install(self, destination, selected):
        if not self._guard.acquire(blocking=False): return {'error': '正在处理，请稍候'}
        self._status.update(busy=True, results=[], stage='正在安装 Surface Studio…', installed='')
        try:
            choices = {i['path']: i for i in self._items if i.get('supported')}
            if any(path not in choices for path in selected): raise ValueError('请重新检测 Blender 后再安装')
            executable = core.install_application(PAYLOAD, destination)
            self._status['installed'] = str(executable)
            results = [{'ok': True, 'title': 'Surface Studio', 'message': '软件已安装，原有 data 数据保留'}]
            self._status['results'] = results
            try: core.create_shortcuts(executable)
            except Exception as exc: results.append({'ok': False, 'title': '快捷方式', 'message': str(exc)})
            installed_profiles = set()
            for path in selected:
                info = choices[path]
                if info.get('host') == 'SketchUp':
                    title = 'SketchUp ' + info['version_string']
                    try:
                        installer_sketchup.install(info, PAYLOAD/'SurfaceStudio-SketchUp.rbz', executable.parent/'data/installer-backups')
                        results.append({'ok': True, 'title': title, 'message': '插件已安装，重新启动 SketchUp 后生效'})
                    except Exception as exc:
                        results.append({'ok': False, 'title': title, 'message': str(exc)})
                    continue
                # Two patch versions often share one Blender user configuration.
                profile = (os.path.normcase(info['config']), os.path.normcase(info['scripts']))
                if profile in installed_profiles:
                    try:
                        core.worker(path, 'verify', ROOT/'installer_blender.py', {'ss_exe': str(executable)})
                        results.append({'ok': True, 'title': 'Blender '+info['version_string'], 'message': '共享配置中的插件已验证，无需重复安装'})
                    except Exception as exc:
                        results.append({'ok': False, 'title': 'Blender '+info['version_string'], 'message': str(exc)})
                    continue
                self._status['stage'] = '正在为 Blender '+info['version_string']+' 安装并验证插件…'
                try:
                    result = core.install_blender(info, executable, PAYLOAD/'surface_studio_bridge.zip',
                                                  ROOT/'installer_blender.py', executable.parent/'data/installer-backups')
                    results.append({'ok': True, 'title': 'Blender '+info['version_string'],
                                    'message': '插件已启用 · SS 路径已配置 · 重启验证通过', 'backup': result['backup']})
                    installed_profiles.add(profile)
                except Exception as exc:
                    results.append({'ok': False, 'title': 'Blender '+info['version_string'], 'message': str(exc)})
            self._status['stage'] = '安装完成' if all(r['ok'] for r in results) else 'SS 已安装，部分项目需要处理后重试'
            report = executable.parent/'data/installer-report.json'
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({'software': '1.7.0', 'addon': '1.3.1', 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
            return {'results': results, 'installed': str(executable)}
        except Exception as exc:
            self._status['stage'] = '安装未完成'
            return {'error': str(exc)}
        finally:
            self._status['busy'] = False
            self._guard.release()

    def launch(self):
        executable = self._status.get('installed')
        if executable and not self._status['busy']:
            core.spawn([executable], cwd=str(Path(executable).parent))
            return True
        return False

    def can_close(self):
        return not self._status['busy']


def main():
    global UPDATE_ARGS
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--update-destination');parser.add_argument('--ready-file');parser.add_argument('--wait-pids')
    args=parser.parse_args()
    if args.update_destination:
        if not args.ready_file or not args.wait_pids:raise ValueError('更新参数不完整')
        UPDATE_ARGS=args
    import webview
    # One setup process per desktop session prevents competing preference writes.
    import ctypes
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\SurfaceStudioSetup')
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(0, 'Surface Studio 安装器已在运行。', 'Surface Studio', 0x40)
        return
    api = Setup()
    window = webview.create_window('Surface Studio · 安装与 Blender 连接', str(ROOT/'installer_ui.html'),
                                  js_api=api, width=920, height=820, min_size=(760, 660),
                                  background_color='#edf3f3')
    api._window = window
    window.events.closing += api.can_close
    try:
        webview.start(gui='edgechromium', private_mode=True)
    finally:
        ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, '安装器无法启动：\n'+str(exc)+'\n请确认已安装 Microsoft Edge WebView2 Runtime。', 'Surface Studio', 0x10)
