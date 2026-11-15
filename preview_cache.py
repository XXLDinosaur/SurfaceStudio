"""Persistent HDR previews, coalesced decodes and cancellable background warming."""
from collections import OrderedDict
from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path
import secrets
import threading
import time

from PIL import Image


class HDRPreviewCache:
    def __init__(self, memory_limit=32*1024*1024):
        self._stripes = [threading.Lock() for _ in range(64)]
        self._condition = threading.Condition()
        self._active = self._foreground_waiting = 0
        self._memory_lock = threading.Lock()
        self._memory = OrderedDict()
        self._memory_bytes = 0
        self._memory_limit = memory_limit
        self._warm_lock = threading.Lock()
        self._thread = None
        self._pending = None
        self._generation = 0
        self._progress = dict(total=0, ready=0, failed=0)

    @staticmethod
    def _read(path):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None
        if len(data) <= 20 or data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            return None
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except (OSError, ValueError):
            return None
        return data

    @staticmethod
    def _encode(image):
        stream = io.BytesIO()
        image.save(stream, 'WEBP', quality=88, method=4)
        return stream.getvalue()

    @staticmethod
    def _write(path, data):
        temporary = path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _remember(self, key, data):
        with self._memory_lock:
            previous = self._memory.pop(key, None)
            if previous is not None:
                self._memory_bytes -= len(previous)
            if len(data) <= self._memory_limit:
                self._memory[key] = data
                self._memory_bytes += len(data)
            while self._memory_bytes > self._memory_limit:
                _, removed = self._memory.popitem(last=False)
                self._memory_bytes -= len(removed)

    @contextmanager
    def _decode_slot(self, background):
        with self._condition:
            if not background:
                self._foreground_waiting += 1
            try:
                self._condition.wait_for(lambda: self._active < 2 and
                                         (not background or self._foreground_waiting == 0))
                self._active += 1
            finally:
                if not background:
                    self._foreground_waiting -= 1
        try:
            yield
        finally:
            with self._condition:
                self._active -= 1
                self._condition.notify_all()

    def get(self, path, size, cache_dir, decode, *, background=False):
        path = Path(path).resolve()
        stat = path.stat()
        size = max(1, min(2048, int(size)))
        signature = f'hdr-preview-v1|{os.path.normcase(str(path))}|{stat.st_mtime_ns}|{stat.st_size}'
        key = hashlib.sha256(signature.encode('utf-8')).hexdigest()
        cache_dir = Path(cache_dir).resolve()
        target = cache_dir/f'hdr-v1-{key}-{size}.webp'
        memory_key = str(target)
        with self._memory_lock:
            data = self._memory.get(memory_key)
            if data is not None:
                self._memory.move_to_end(memory_key)
                return data
        data = self._read(target)
        if data is not None:
            if not background:
                self._remember(memory_key, data)
            return data
        # Different requested sizes share one source lock and one base decode.
        with self._stripes[int(key[:8], 16) % len(self._stripes)]:
            data = self._read(target)
            if data is None:
                cache_dir.mkdir(parents=True, exist_ok=True)
                base_size = 1024 if size <= 1024 else 2048
                master = cache_dir/f'hdr-v1-{key}-base{base_size}.webp'
                master_data = self._read(master)
                if master_data is None:
                    # A previously generated large base can also serve smaller views.
                    larger = cache_dir/f'hdr-v1-{key}-base2048.webp'
                    master_data = self._read(larger) if base_size == 1024 else None
                if master_data is None:
                    with self._decode_slot(background):
                        with decode(path, base_size) as image:
                            master_data = self._encode(image)
                        self._write(master, master_data)
                with Image.open(io.BytesIO(master_data)) as image:
                    if max(image.size) <= size:
                        data = master_data
                    else:
                        image.thumbnail((size, size), Image.Resampling.LANCZOS)
                        data = self._encode(image)
                self._write(target, data)
        if not background:
            self._remember(memory_key, data)
        return data

    def schedule(self, entries, cache_dir, decode, resolve=Path):
        entries = tuple(entries)
        with self._warm_lock:
            self._generation += 1
            self._pending = (self._generation, entries, cache_dir, decode, resolve)
            self._progress = dict(total=len(entries), ready=0, failed=0)
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._warm, name='SS HDR previews', daemon=True)
                self._thread.start()

    def _warm(self):
        while True:
            with self._warm_lock:
                work, self._pending = self._pending, None
                if work is None:
                    self._thread = None
                    return
            generation, entries, directory, decode, resolve = work
            for entry in entries:
                with self._warm_lock:
                    if generation != self._generation:
                        break
                succeeded = False
                try:
                    self.get(resolve(entry), 480, directory, decode, background=True)
                    succeeded = True
                except Exception:
                    pass  # One inaccessible or corrupt original must not stop the library.
                with self._warm_lock:
                    if generation == self._generation:
                        self._progress['ready' if succeeded else 'failed'] += 1
                time.sleep(.015)

    def cancel(self):
        with self._warm_lock:
            self._generation += 1
            self._pending = None

    def wait(self, timeout=None):
        with self._warm_lock:
            thread = self._thread
        if thread:
            thread.join(timeout)
            return not thread.is_alive()
        return True

    def status(self):
        with self._warm_lock:
            return {**self._progress, 'running': self._thread is not None and self._thread.is_alive()}
