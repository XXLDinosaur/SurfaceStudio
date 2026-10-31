import json
from pathlib import Path
import shutil
import subprocess
import time
import threading
from urllib.request import Request, urlopen
import bpy
from bpy.props import StringProperty
from .native_material import export_snapshot


def register_source(directory):
    from . import executable
    from .service import resolve_service
    base = resolve_service(executable())
    with urlopen(base+'/api/library', timeout=5) as response:
        library = json.load(response)
    request = Request(base+'/api/blender/library-source',
        data=json.dumps({'directory':str(directory)}).encode(),
        headers={'Content-Type':'application/json','X-Studio-Token':library['token']})
    with urlopen(request, timeout=5) as response: json.load(response)


class SURFACESTUDIO_OT_export(bpy.types.Operator):
    bl_idname = 'surface_studio.export_material'
    bl_label = '添加到 SS'
    bl_description = '将当前活动材质直接保存到 SS 设置的材质保存位置，并加入未分类'
    asset_name: StringProperty(name='材质名称', maxlen=100)
    _process = None
    _stage = None
    _timer = None
    _material = None

    @classmethod
    def poll(cls, context):
        return bool(context.object and context.object.active_material)

    def invoke(self, context, event):
        self._material = context.object.active_material
        self.asset_name = self._material.name
        return self.execute(context)

    def execute(self, context):
        try:
            self._registering = False
            material = self._material or context.object.active_material
            try:
                from . import executable
                from .service import resolve_service
                with urlopen(resolve_service(executable())+'/api/library', timeout=3) as response:
                    library = json.load(response)
            except Exception as exc:
                raise ValueError('请先打开 SS，再点击“添加到 SS”') from exc
            directory = library.get('effectiveMaterialSaveRoot')
            if not directory: raise ValueError('请先更新 SS，在材质库设置中确认材质保存位置')
            self._stage, self._final = export_snapshot(material, directory, self.asset_name or material.name)
            self._log = (self._stage/'preview.log').open('w', encoding='utf-8')
            self._process = subprocess.Popen([bpy.app.binary_path, '--background', '--factory-startup',
                '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python',
                str(Path(__file__).with_name('preview_worker.py')), '--', str(self._stage)],
                stdout=self._log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self._started = time.monotonic()
            self._timer = context.window_manager.event_timer_add(.5, window=context.window)
            context.window_manager.modal_handler_add(self)
            context.workspace.status_text_set('SS：正在生成材质预览，Esc 可取消')
            return {'RUNNING_MODAL'}
        except Exception as exc:
            self.cleanup(context)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

    def modal(self, context, event):
        if getattr(self, '_registering', False):
            if event.type != 'TIMER' or self._registration['done'] is None: return {'PASS_THROUGH'}
            success = self._registration['done']
            self.cleanup(context)
            self.report({'INFO'} if success else {'WARNING'}, '已添加到 SS · 未分类' if success else '材质已保存，SS 暂未响应；重新扫描材质库即可显示：'+str(self._final))
            return {'FINISHED'}
        if event.type == 'ESC' or time.monotonic()-self._started > 600:
            self.cleanup(context)
            self.report({'WARNING'}, '导出已取消或超时，未修改原材质')
            return {'CANCELLED'}
        if event.type != 'TIMER' or self._process.poll() is None:
            return {'PASS_THROUGH'}
        try:
            if self._process.returncode or not (self._stage/'preview.png').is_file():
                error = self._stage/'preview-error.txt'
                raise ValueError('预览生成失败：'+(error.read_text(encoding='utf-8') if error.exists() else '请检查材质及渲染设置'))
            self._log.close(); (self._stage/'preview.log').unlink(missing_ok=True)
            self._stage.rename(self._final)
            self._stage = None
            self._registering = True
            self._registration = status = {'done':None}
            directory = self._final.parent
            def notify():
                for attempt in range(10):
                    try:
                        register_source(directory)
                        status['done'] = True
                        return
                    except Exception: time.sleep(1)
                status['done'] = False
            threading.Thread(target=notify, daemon=True).start()
            context.workspace.status_text_set('SS：材质已保存，正在加入未分类…')
            return {'RUNNING_MODAL'}
        except Exception as exc:
            self.cleanup(context); self.report({'ERROR'},str(exc))
            return {'CANCELLED'}

    def cleanup(self, context):
        if self._process and self._process.poll() is None:
            self._process.kill(); self._process.wait(timeout=10)
        if getattr(self,'_log',None): self._log.close()
        if self._timer: context.window_manager.event_timer_remove(self._timer); self._timer=None
        context.workspace.status_text_set(None)
        if self._stage and self._stage.exists():
            # Only remove the private, newly created staging folder.
            assert self._stage.resolve().parent == self._final.parent.resolve() and self._stage.name.startswith('.ss-export-')
            shutil.rmtree(self._stage)
            self._stage=None

    def cancel(self, context):
        self.cleanup(context)
