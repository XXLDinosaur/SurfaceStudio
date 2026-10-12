"""Packaged Windows entry point. Runs without requiring a Python installation."""
import ctypes, os, sys, threading
from pathlib import Path
from urllib.request import urlopen
import json

ROOT = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
URL = 'http://127.0.0.1:47831'
os.environ['SURFACE_STUDIO_DATA'] = str(ROOT / 'data')

class WindowControls:
    def __init__(self):
        self._window = None
        self._maximized = False

    def minimize(self):
        self._window.minimize()

    def toggle_maximize(self):
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()
        return self._maximized

    def close(self):
        self._window.destroy()

    def window_state(self):
        return {'maximized': self._maximized}

    def start_material_drag(self, filename):
        """Expose a real Windows CF_HDROP file, not a browser image/URL drag."""
        import re
        from System import Action, Array, String
        from System.Windows.Forms import DataObject, DragDropEffects, Control, MouseButtons
        path = Path(filename).resolve()
        allowed = (ROOT/'data/blender/drops').resolve()
        if path.parent != allowed or path.suffix != '.ssmat' or not re.fullmatch('[a-f0-9]{32}', path.stem):
            raise ValueError('无效的材质拖拽文件')
        if not path.is_file(): raise ValueError('拖拽材质已失效，请重试')
        result = {'dropped': False}
        def drag():
            try:
                if not (int(Control.MouseButtons) & int(MouseButtons.Left)): return
                data = DataObject()
                from System.Windows.Forms import DataFormats
                data.SetData(DataFormats.FileDrop, Array[String]([str(path)]))
                from material_drag import install_drop_guard
                form = self._window.native
                guard = install_drop_guard(form)
                try:
                    result['dropped'] = form.DoDragDrop(data, DragDropEffects.Copy) == DragDropEffects.Copy
                finally:
                    form.QueryContinueDrag -= guard
            except Exception as exc:
                result['error'] = str(exc)
        self._window.native.Invoke(Action(drag))
        if result.get('error'): raise RuntimeError(result['error'])
        return result

    def bounds(self):
        w = self._window
        return {'x': w.x, 'y': w.y, 'width': w.width, 'height': w.height}

    def resize_bounds(self, x, y, width, height):
        if self._maximized:
            return
        width, height = max(980, min(10000, int(width))), max(680, min(10000, int(height)))
        self._window.resize(width, height)
        self._window.move(int(x), int(y))

    def _state_changed(self, maximized):
        self._maximized = maximized
        try:
            self._window.evaluate_js('window.surfaceWindowState && window.surfaceWindowState(%s)' % ('true' if maximized else 'false'))
        except Exception:
            pass

def open_window():
    import webview
    api = WindowControls()
    webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = True
    window = webview.create_window(
        'SURFACE — 私人材质工作室', URL, js_api=api,
        width=1600, height=1040, min_size=(980, 680),
        frameless=True, easy_drag=False, resizable=True, shadow=True,
        background_color='#263640', text_select=True,
    )
    api._window = window
    window.events.maximized += lambda: api._state_changed(True)
    window.events.restored += lambda: api._state_changed(False)
    webview.start(gui='edgechromium', private_mode=False, storage_path=str(ROOT/'data/webview-profile'))

def main():
    try:
        with urlopen(URL+'/api/health',timeout=2) as response:
            if json.load(response).get('app')=='Surface Studio':
                open_window(); return
    except Exception: pass
    import server
    saved=server.read_json(server.DATA/'index.json',None)
    if saved and saved.get('root')==server.CONFIG['root']:
        server.INDEX=saved
        server.ASSETS={a['id']:a for a in saved['assets']}
    else: server.scan()
    http=server.ThreadingHTTPServer(('127.0.0.1',47831),server.Handler)
    # Keep the local service available to the Blender bridge after closing the window.
    threading.Thread(target=http.serve_forever,daemon=False).start()
    open_window()

if __name__=='__main__':
    try: main()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(0,'Surface Studio 启动失败：\n'+str(exc),'Surface Studio',0x10)
