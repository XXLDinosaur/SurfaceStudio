"""Match the native window outline to the UI's continuous corner profile."""
import math


def outline(width, height, radius, exponent=2 ** 1.5):
    r = min(radius, width / 2, height / 2)
    points = []
    # Sample the superellipse, with exact tangent endpoints on each straight edge.
    for cx, cy, start in [(width-r, r, -90), (width-r, height-r, 0),
                          (r, height-r, 90), (r, r, 180)]:
        for i in range(65):
            angle = math.radians(start + i * 90 / 64)
            c, s = math.cos(angle), math.sin(angle)
            def power(v):
                return 0.0 if abs(v) < 1e-12 else math.copysign(abs(v) ** (2 / exponent), v)
            points.append((cx + r * power(c), cy + r * power(s)))
    return points


def apply_shape(form, scale=1.0, smooth=True):
    from System import Array
    from System.Drawing import PointF, Region
    from System.Drawing.Drawing2D import GraphicsPath
    from System.Windows.Forms import FormWindowState
    old = form.Region
    if form.WindowState == FormWindowState.Maximized:
        form.Region = None
    elif form.WindowState != FormWindowState.Minimized:
        path = GraphicsPath()
        try:
            points = outline(form.Width, form.Height, 48 * scale, 2 ** 1.5 if smooth else 2)
            path.AddPolygon(Array[PointF]([PointF(x, y) for x, y in points]))
            form.Region = Region(path)
        finally:
            path.Dispose()
    else:
        return
    if old is not None: old.Dispose()
