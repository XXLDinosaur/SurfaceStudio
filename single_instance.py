"""Per-session desktop ownership and activation, including startup races."""
import ctypes
from ctypes import wintypes


class DesktopInstance:
    def __init__(self, name=r'Local\SurfaceStudio.Desktop', title='SURFACE — 私人材质工作室'):
        self.title = title
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateMutexW.restype = wintypes.HANDLE
        k.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateEventW.restype = wintypes.HANDLE
        k.SetEvent.argtypes = [wintypes.HANDLE]
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        # Open the event before claiming ownership, so launches during startup
        # cannot lose their notification before the owner's window exists.
        self.event = k.CreateEventW(None, False, False, name+'.Activate')
        if not self.event: raise ctypes.WinError(ctypes.get_last_error())
        self.mutex = k.CreateMutexW(None, False, name)
        error = ctypes.get_last_error()
        if not self.mutex:
            k.CloseHandle(self.event)
            raise ctypes.WinError(error)
        self.primary = error != 183

    def activate(self):
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user.FindWindowW.restype = wintypes.HWND
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
        hwnd = user.FindWindowW(None, self.title)
        if hwnd:
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value: user.AllowSetForegroundWindow(pid.value)
        if not self.kernel.SetEvent(self.event): raise ctypes.WinError(ctypes.get_last_error())

    def wait(self, milliseconds=1000):
        result = self.kernel.WaitForSingleObject(self.event, milliseconds)
        if result == 0xFFFFFFFF: raise ctypes.WinError(ctypes.get_last_error())
        return result == 0

    def close(self):
        for name in ('mutex', 'event'):
            handle = getattr(self, name, None)
            if handle:
                self.kernel.CloseHandle(handle)
                setattr(self, name, None)
