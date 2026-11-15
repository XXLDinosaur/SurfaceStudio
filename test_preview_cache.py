import importlib
import io
import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image


class PreviewCacheTests(unittest.TestCase):
    def cache(self):
        self.assertIsNotNone(importlib.util.find_spec('preview_cache'), 'HDR 预览缓存优化尚未实现')
        return importlib.import_module('preview_cache').HDRPreviewCache()

    def test_persistent_cache_and_shared_master_across_sizes(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); path=root/'天空.hdr';path.write_bytes(b'original')
            calls=[]
            def decode(path,size):
                calls.append(size);return Image.new('RGB',(128,64),(120,140,160))
            first=cache.get(path,64,root/'cache',decode)
            self.assertEqual(Image.open(io.BytesIO(first)).size,(64,32))
            cache.get(path,96,root/'cache',decode)
            self.assertEqual(calls,[1024])
            fresh=self.cache()
            def forbidden(*args):raise AssertionError('Persistent cache unexpectedly decoded the source')
            self.assertEqual(fresh.get(path,64,root/'cache',forbidden),first)
            fresh.get(path,120,root/'cache',forbidden)

    def test_same_source_concurrent_requests_decode_once(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'same.hdr';path.touch();calls=[]
            def decode(*args):
                calls.append(1);time.sleep(.04);return Image.new('RGB',(128,64))
            with ThreadPoolExecutor(max_workers=8) as pool:
                results=list(pool.map(lambda size:cache.get(path,size,root/'cache',decode),[64,96,120,64,96,120,64,96]))
            self.assertTrue(all(results));self.assertEqual(len(calls),1)

    def test_source_changes_invalidate_even_if_mtime_unchanged(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'change.hdr';path.write_bytes(b'a');calls=[]
            def decode(*args):calls.append(1);return Image.new('RGB',(8,4),(len(calls)*60,0,0))
            first=cache.get(path,64,root/'cache',decode);stat=path.stat()
            path.write_bytes(b'new contents');os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            second=cache.get(path,64,root/'cache',decode)
            self.assertNotEqual(first,second);self.assertEqual(len(calls),2)
            os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000))
            cache.get(path,64,root/'cache',decode);self.assertEqual(len(calls),3)

    def test_background_warms_card_cache_and_continues_after_bad_image(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);good=root/'good.hdr';bad=root/'bad.hdr';good.touch();bad.touch()
            def decode(path,size):
                if path.name=='bad.hdr':raise TypeError('unexpected decoder error')
                return Image.new('RGB',(8,4))
            cache.schedule([bad,good],root/'cache',decode)
            self.assertTrue(cache.wait(5))
            status=cache.status();self.assertEqual(status['ready'],1);self.assertEqual(status['failed'],1)
            self.assertFalse(status['running'])
            def forbidden(*args):raise AssertionError('Background did not warm the card cache')
            cache.get(good,480,root/'cache',forbidden)

    def test_cancel_background_work(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[root/f'{i}.hdr' for i in range(8)]
            for path in paths:path.touch()
            entered=threading.Event();release=threading.Event();calls=[]
            def decode(*args):
                calls.append(1);entered.set();self.assertTrue(release.wait(5));return Image.new('RGB',(8,4))
            cache.schedule(paths,root/'cache',decode)
            self.assertTrue(entered.wait(5));cache.cancel();release.set()
            self.assertTrue(cache.wait(5));self.assertEqual(len(calls),1)

    def test_total_decode_concurrency_is_bounded(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[root/f'{i}.hdr' for i in range(8)]
            for path in paths:path.touch()
            lock=threading.Lock();active=0;peak=0
            def decode(*args):
                nonlocal active,peak
                with lock:active+=1;peak=max(peak,active)
                time.sleep(.03)
                with lock:active-=1
                return Image.new('RGB',(8,4))
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda path:cache.get(path,480,root/'cache',decode),paths))
            self.assertLessEqual(peak,2)

    def test_new_scan_replaces_pending_warmup(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=[root/f'old{i}.hdr' for i in range(4)];new=root/'new.hdr'
            for path in [*old,new]:path.touch()
            entered=threading.Event();release=threading.Event();decoded=[]
            def decode(path,size):
                decoded.append(path.name)
                if path.name=='old0.hdr':entered.set();self.assertTrue(release.wait(5))
                return Image.new('RGB',(8,4))
            cache.schedule(old,root/'cache',decode);self.assertTrue(entered.wait(5))
            cache.schedule([new],root/'cache',decode);release.set()
            self.assertTrue(cache.wait(5))
            self.assertEqual(decoded,['old0.hdr','new.hdr'])
            self.assertEqual(cache.status()['total'],1);self.assertEqual(cache.status()['ready'],1)

    def test_large_preview_has_its_own_reusable_base(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'large.hdr';path.touch();sizes=[]
            def decode(path,size):sizes.append(size);return Image.new('RGB',(size,size//2))
            cache.get(path,480,root/'cache',decode)
            large=cache.get(path,9000,root/'cache',decode)
            self.assertEqual(Image.open(io.BytesIO(large)).size,(2048,1024))
            cache.get(path,1600,root/'cache',decode)
            self.assertEqual(sizes,[1024,2048])

    def test_corrupt_cache_files_are_regenerated(self):
        cache=self.cache()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'original.hdr';path.touch();calls=[]
            def decode(*args):calls.append(1);return Image.new('RGB',(128,64))
            cache.get(path,64,root/'cache',decode)
            for cached in (root/'cache').glob('*.webp'):
                cached.write_bytes(b'RIFF'+b'\0'*4+b'WEBP'+b'broken image payload')
            fresh=self.cache();data=fresh.get(path,64,root/'cache',decode)
            self.assertEqual(len(calls),2,'损坏缓存必须从原图重建')
            self.assertEqual(Image.open(io.BytesIO(data)).size,(64,32))


if __name__=='__main__':unittest.main()
