"""Constrain native material file drops to Blender before OLE delivers data."""
import ctypes
from ctypes import wintypes
from pathlib import PureWindowsPath


def pointer_target():
    """Read the actual hit window, not the foreground/drag source window."""
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user.GetCursorPos.restype = wintypes.BOOL
    user.WindowFromPoint.argtypes = [wintypes.POINT]
    user.WindowFromPoint.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    user.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    point, pid = wintypes.POINT(), wintypes.DWORD()
    if not user.GetCursorPos(ctypes.byref(point)): return False
    window = user.WindowFromPoint(point)
    if not window or not user.GetWindowThreadProcessId(window, ctypes.byref(pid)): return False
    process = kernel.OpenProcess(0x1000, False, pid.value)
    if not process: return False
    try:
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)): return False
        name = PureWindowsPath(path.value).name.lower()
        rect = wintypes.RECT()
        if not user.ScreenToClient(window, ctypes.byref(point)) or not user.GetClientRect(window, ctypes.byref(rect)):
            return None
        return name, pid.value, [point.x, point.y, rect.right, rect.bottom]
    finally:
        kernel.CloseHandle(process)


def blender_under_pointer():
    hit = pointer_target()
    return bool(hit and hit[0] == 'blender.exe')


def route_release(release):
    hit = pointer_target()
    if hit and hit[0] == 'sketchup.exe':
        release.append(hit)
    return bool(hit and hit[0] == 'blender.exe')


def install_drop_guard(form, target_check=blender_under_pointer):
    from System.Windows.Forms import DragAction

    def guard(sender, event):
        if event.EscapePressed:
            event.Action = DragAction.Cancel
        elif not (event.KeyState & 1):  # MK_LBUTTON; runs before IDropTarget.Drop.
            try:
                allowed = target_check()
            except Exception:
                allowed = False
            if not allowed:
                event.Action = DragAction.Cancel

    form.QueryContinueDrag += guard
    return guard
