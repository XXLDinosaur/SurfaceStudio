import base64,hashlib,io,json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import updater as u
import installer as setup
import installer_core as core
from update_handoff import validate_destination

class UpdateTests(unittest.TestCase):
    def test_desktop_handoff_waits_for_ready_and_keeps_app_on_failure(self):
        import desktop
        with tempfile.TemporaryDirectory() as t:
            manager=u.Updater(t);api=desktop.WindowControls();api._updater=manager;api._window=Mock()
            package=Path(t)/u.SETUP;package.write_bytes(b'test')
            with patch.object(desktop.sys,'frozen',True,create=True),patch.object(core,'processes',return_value=[{'Name':'blender.exe'}]),patch.object(core,'spawn') as spawn:
                self.assertIn('error',api.install_update());spawn.assert_not_called();api._window.destroy.assert_not_called()
            def spawn_ready(command,**kwargs):
                api._window.destroy.assert_not_called()
                Path(command[command.index('--ready-file')+1]).write_text('{}')
                return Mock(poll=lambda:None)
            for ready in (False,True):
                with patch.object(desktop.sys,'frozen',True,create=True),patch.object(core,'processes',return_value=[]),patch.object(manager,'verified_package',return_value=package),patch.object(core,'spawn',side_effect=spawn_ready if ready else lambda *a,**k:Mock(poll=lambda:1)):
                    self.assertTrue(api.install_update()['ok'])
                    for _ in range(100):
                        if not manager.lock.locked():break
                        time.sleep(.01)
                    self.assertFalse(manager.lock.locked())
                if ready:api._window.destroy.assert_called_once()
                else:api._window.destroy.assert_not_called();self.assertEqual(manager.status()['phase'],'ready')

    def setUp(self):
        self.key=Ed25519PrivateKey.generate();self.pub=base64.b64encode(self.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode();self.payload=b'MZ-isolated-installer-payload'
        self.data={'format':'surface-studio-update-v1','version':'1.6.0','asset':u.SETUP,'size':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()};self.raw=json.dumps(self.data).encode();self.sig=self.key.sign(self.raw)
        self.base='https://github.com/'+u.REPO+'/releases/download/v1.6.0/'
        self.release={'tag_name':'v1.6.0','draft':False,'prerelease':False,'body':'测试新版','assets':[{'name':n,'state':'uploaded','browser_download_url':self.base+n} for n in ['surface-update.json','surface-update.sig',u.SETUP]]}
    def fetch(self,url,limit):
        return {u.LATEST:json.dumps(self.release).encode(),self.base+'surface-update.json':self.raw,self.base+'surface-update.sig':self.sig}[url]
    def test_signed_new_release_download_integrity_and_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            m=u.Updater(t);verify=u.verify_manifest
            with patch.object(u,'fetch',self.fetch),patch.object(u,'verify_manifest',side_effect=lambda raw,sig,rel:verify(raw,sig,rel,self.pub)):
                m._check()
            self.assertEqual(m.status()['phase'],'available')
            dest=Path(t)/u.SETUP
            u.download_verified(self.base+u.SETUP,dest,m.manifest,opener=lambda url:io.BytesIO(self.payload))
            m.package=dest;self.assertEqual(m.verified_package(),dest)
            dest.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):m.verified_package()
    def test_reject_bad_signature_version_and_prerelease(self):
        for raw,sig,release in [(self.raw+b' ',self.sig,self.release),(self.raw,b'bad',self.release),(self.raw,self.sig,{**self.release,'tag_name':'v2.0.0'}),(self.raw,self.sig,{**self.release,'prerelease':True})]:
            with self.assertRaises(Exception):u.verify_manifest(raw,sig,release,self.pub)
        self.assertGreater(u.version('1.10.0'),u.version('1.9.9'))
        with self.assertRaises(ValueError):u.version('1.6.0-beta')
    def test_old_release_no_download_and_network_failure_keeps_running(self):
        with tempfile.TemporaryDirectory() as t:
            m=u.Updater(t);self.release['tag_name']='v1.4.0'
            with patch.object(u,'fetch',self.fetch):m._check()
            self.assertEqual(m.state['phase'],'current');self.assertIsNone(m.manifest)
            with patch.object(u,'fetch',side_effect=OSError('offline')):
                m.check()
                for i in range(100):
                    if not m.lock.locked():break
                    time.sleep(.01)
            self.assertEqual(m.state['phase'],'error');self.assertTrue(Path(t).exists())
            m.set_auto(False);self.assertFalse(u.Updater(t).auto)
    def test_partial_and_corrupt_download_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)/u.SETUP
            for data in [self.payload[:-1],self.payload+b'x',b'x'*len(self.payload)]:
                with self.assertRaises(ValueError):u.download_verified(self.base+u.SETUP,dest,self.data,opener=lambda url:io.BytesIO(data))
                self.assertFalse(dest.exists());self.assertEqual(list(Path(t).glob('*.partial')),[])
        self.assertFalse(u.allowed('http://github.com/x'));self.assertFalse(u.allowed('https://evil.example/x'))
    def test_update_mode_installs_into_original_folder_and_preserves_data(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);dest=root/'原软件';payload=root/'payload';payload.mkdir();(dest/'data/updates').mkdir(parents=True)
            (payload/'Surface Studio.exe').write_bytes(b'new version');(dest/'Surface Studio.exe').write_bytes(b'old version');(dest/'data/config.json').write_text('original root');(dest/'data/state.json').write_text('favorites')
            args=SimpleNamespace(update_destination=str(dest),ready_file=str(dest/'data/updates/handoff-test.json'),wait_pids='123')
            with patch.object(setup,'UPDATE_ARGS',args),patch.object(setup,'PAYLOAD',payload),patch('update_handoff.wait_for_previous') as wait,patch.object(core,'processes',return_value=[]),patch.object(core,'discover',return_value=[]),patch.object(core,'create_shortcuts'):
                api=setup.Setup();self.assertTrue(api.defaults()['updateMode']);self.assertTrue(Path(args.ready_file).exists());result=api.auto_update();wait.assert_called_once_with([123])
                self.assertNotIn('error',result)
            self.assertEqual((dest/'Surface Studio.exe').read_bytes(),b'new version');self.assertEqual((dest/'data/state.json').read_text(),'favorites');self.assertEqual((dest/'data/config.json').read_text(),'original root');self.assertEqual(next((dest/'data/installer-backups').rglob('*.exe')).read_bytes(),b'old version')
            with self.assertRaises(ValueError):validate_destination(dest,root/'outside.json')
    def test_update_copy_failure_keeps_original(self):
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)/'SS';dest.mkdir();exe=dest/'Surface Studio.exe';exe.write_bytes(b'old')
            with patch.object(core,'processes',return_value=[]):
                with self.assertRaises(RuntimeError):core.install_application(Path(t)/'missing',dest)
            self.assertEqual(exe.read_bytes(),b'old')

if __name__=='__main__':unittest.main()
