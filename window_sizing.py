"""Startup geometry in physical pixels, matching WinForms WorkingArea."""
import math

def startup_geometry(left,top,width,height,scale):
    if width<=0 or height<=0 or not math.isfinite(scale) or scale<=0:
        raise ValueError('Invalid monitor geometry')
    margin=min(round(16*scale),max(0,min(width,height)//20))
    available_width=max(1,width-2*margin)
    available_height=max(1,height-2*margin)
    window_width=min(round(1600*scale),available_width)
    window_height=min(round(1040*scale),available_height)
    return (left+(width-window_width)//2,top+(height-window_height)//2,
            window_width,window_height,
            min(round(980*scale),window_width),min(round(680*scale),window_height))

def fit_startup_window(window):
    # before_show runs synchronously on the UI thread, after the native HWND
    # exists. Using that HWND's DPI avoids virtualized/global screen metrics.
    from ctypes import windll, wintypes
    from System.Drawing import Size,Point
    from System.Windows.Forms import Screen,FormStartPosition
    form=window.native
    area=Screen.FromControl(form).WorkingArea
    dpi=windll.user32.GetDpiForWindow
    dpi.argtypes=[wintypes.HWND];dpi.restype=wintypes.UINT
    scale=(dpi(form.Handle.ToInt64()) or 96)/96
    x,y,width,height,min_width,min_height=startup_geometry(area.X,area.Y,area.Width,area.Height,scale)
    form.MinimumSize=Size(min_width,min_height)
    form.Size=Size(width,height)
    form.StartPosition=FormStartPosition.Manual
    form.Location=Point(x,y)
