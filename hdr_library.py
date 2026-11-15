"""Independent HDR environment library; preview conversion never alters originals."""
import hashlib
import os
import re
from pathlib import Path

from material_names import apply_metadata
from hdr_categories import LABELS, classify_hdr


def validate_hdr_root(source, other_roots):
    if not isinstance(source, str):
        raise ValueError('HDR 图库路径无效')
    if not source.strip():
        return ''
    path = Path(source.strip())
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('HDR 图库路径不存在，请填写完整目录')
    path = path.resolve()
    for other in other_roots:
        if other:
            other = Path(other).resolve()
            if path.is_relative_to(other) or other.is_relative_to(path):
                raise ValueError('HDR 图库请使用独立目录，不能与其他素材来源重叠')
    return str(path)


def scan_hdrs(source, warnings):
    if not source:
        return []
    root = Path(source).resolve()
    if not root.is_dir():
        warnings.append('HDR 图库路径不存在：' + str(root))
        return []
    result = []
    for directory, dirs, names in os.walk(root, followlinks=False,
                                          onerror=lambda e: warnings.append('HDR 图库：' + str(e))):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and
                         not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_junction())
        for name in sorted(names):
            path = Path(directory)/name
            if name.startswith('.') or path.suffix.lower() not in ('.hdr', '.exr'):
                continue
            try:
                if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                    continue
                relative = path.relative_to(root)
                key = 'hdr:' + relative.as_posix()
                ident = hashlib.sha1((os.path.normcase(str(root))+'|'+key).encode('utf-8')).hexdigest()[:16]
                stat = path.stat()
                resolution = re.search(r'(?:^|[_ .-])(\d+)k(?:[_ .-]|$)', name, re.I)
                asset = dict(id=ident, assetId=ident, name=path.stem, folder=relative.parent.as_posix(),
                             sourceRoot=str(root), libraryKey=key, kind='hdr', category='HDR',
                             categoryZh='HDR 环境', tags=['HDR', '环境光'], categories=['HDR'],
                             search=relative.as_posix().lower()+' hdr hdri 环境',
                             resolution=resolution.group(1)+'K' if resolution else '—', preview=name,
                             previewRevision=f'{stat.st_mtime_ns}-{stat.st_size}',
                             maps=[dict(name=name, channel='Environment', bytes=stat.st_size,
                                        ext=path.suffix[1:].upper())], bytes=stat.st_size,
                             modified=stat.st_mtime, meta={})
                asset = apply_metadata(asset, path.with_name(name+'.surface.json'))
                category = classify_hdr(asset['name'])
                asset.update(category=category, categoryZh=LABELS[category], categories=[category])
                result.append(asset)
            except OSError as exc:
                warnings.append('HDR '+str(path)+': '+str(exc))
    return result


def hdr_thumbnail(path, size):
    # Lazy imports keep indexing and ordinary materials independent of the decoder.
    import OpenImageIO as oiio
    import numpy as np
    from PIL import Image

    source = oiio.ImageBuf(str(path))
    spec = source.spec()
    if spec.width <= 0 or spec.height <= 0 or spec.nchannels < 1:
        raise ValueError('HDR 预览读取失败：' + source.geterror())
    if spec.width * spec.height > 1073741824:
        raise ValueError('HDR 图片尺寸过大，无法生成预览')
    size = max(1, min(2048, int(size)))
    scale = min(1, size / max(spec.width, spec.height))
    width, height = max(1, round(spec.width*scale)), max(1, round(spec.height*scale))
    thumb = oiio.ImageBufAlgo.resample(source, roi=oiio.ROI(0, width, 0, height, 0, 1, 0, spec.nchannels), nthreads=2)
    pixels = thumb.get_pixels(oiio.FLOAT)
    if pixels is None or thumb.has_error or source.has_error:
        raise ValueError('HDR 预览解码失败：' + (thumb.geterror() or source.geterror()))
    channels = list(spec.channelnames)
    if all(c in channels for c in ('R', 'G', 'B')):
        pixels = pixels[..., [channels.index(c) for c in ('R', 'G', 'B')]]
    elif pixels.shape[-1] < 3:
        pixels = np.repeat(pixels[..., :1], 3, axis=-1)
    else:
        pixels = pixels[..., :3]
    pixels = np.maximum(np.nan_to_num(pixels, nan=0, posinf=1e10, neginf=0), 0)
    pixels = pixels / (1 + pixels)  # Reinhard display mapping; original stays linear/HDR.
    pixels = np.where(pixels <= .0031308, pixels*12.92, 1.055*np.power(pixels, 1/2.4)-.055)
    return Image.fromarray(np.uint8(np.clip(pixels*255, 0, 255)), 'RGB')
