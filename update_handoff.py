"""Update handoff validation and bounded wait for the previous desktop process."""
import os,time
from pathlib import Path

def validate_destination(value,ready):
    destination=Path(value)
    if not destination.is_absolute() or not (destination/'Surface Studio.exe').is_file():raise ValueError('原软件安装位置无效')
    destination=destination.resolve();ready=Path(ready).resolve()
    if ready.parent!=(destination/'data'/'updates').resolve() or not ready.name.startswith('handoff-') or ready.suffix!='.json':raise ValueError('更新交接路径无效')
    return destination,ready

def wait_for_previous(pids,timeout=45):
    if os.name!='nt':raise RuntimeError('仅支持 Windows 自动更新')
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    deadline=time.monotonic()+timeout
    for pid in pids:
        if type(pid) is not int or pid<=0 or pid==os.getpid():raise ValueError('更新进程标识无效')
        handle=kernel.OpenProcess(0x00100000,False,pid)
        if handle:
            try:
                if kernel.WaitForSingleObject(handle,max(0,int((deadline-time.monotonic())*1000)))!=0:raise RuntimeError('旧版 SS 尚未退出，请关闭后重试')
            finally:kernel.CloseHandle(handle)
