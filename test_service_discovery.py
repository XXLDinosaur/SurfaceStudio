import importlib.util,json,socket,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler
import service_discovery
spec=importlib.util.spec_from_file_location('addon_service',Path(__file__).parent/'blender_addon/surface_studio_bridge/service.py')
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
class Health(BaseHTTPRequestHandler):
    instance='test-instance-123456789'
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'app':'Surface Studio','instance':self.instance}).encode())
    def log_message(self,*args):pass
class DiscoveryTests(unittest.TestCase):
    def test_conflict_falls_back_and_plugin_finds_installation(self):
        with socket.socket() as occupied,tempfile.TemporaryDirectory() as folder:
            occupied.bind(('127.0.0.1',0));occupied.listen();port=occupied.getsockname()[1]
            http=service_discovery.bind_server(Health,port)
            self.assertNotEqual(http.server_port,port)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            root=Path(folder);(root/'data').mkdir()
            try:
                service_discovery.publish(root/'data',http.server_port,Health.instance)
                self.assertEqual(service.resolve_service(root/'Surface Studio.exe'),'http://127.0.0.1:'+str(http.server_port))
                service_discovery.publish(root/'data',http.server_port,'stale-instance-123456789')
                with self.assertRaises(ValueError):service.resolve_service(root/'Surface Studio.exe')
                service_discovery.clear(root/'data',Health.instance)
                self.assertTrue((root/'data/service.json').exists())
                service_discovery.clear(root/'data','stale-instance-123456789')
                self.assertFalse((root/'data/service.json').exists())
            finally:http.shutdown();http.server_close();thread.join()
    def test_malformed_record_is_not_used(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').mkdir()
            (root/'data/service.json').write_text(json.dumps({'format':'surface-studio-service-v1','port':'https://evil','instance':'x'*20}))
            with self.assertRaises(ValueError):service.resolve_service(root/'app.exe')
    def test_desktop_lifecycle_publishes_and_clears_actual_port(self):
        from unittest.mock import patch
        import desktop
        import server as app
        saved={name:getattr(app,name) for name in ('DATA','CACHE','CONFIG','INDEX','ASSETS','PORT','SCANNING','SCAN_ERROR')}
        old_url=desktop.URL
        try:
            with tempfile.TemporaryDirectory() as directory,socket.socket() as occupied:
                root=Path(directory);data=root/'data';data.mkdir();materials=root/'materials';materials.mkdir()
                app.DATA=data;app.CACHE=data;app.CONFIG={'root':str(materials)};app.SCANNING=False
                occupied.bind(('127.0.0.1',0));occupied.listen();port=occupied.getsockname()[1]
                original=service_discovery.bind_server
                def open_window(_):
                    self.assertNotEqual(app.PORT,port)
                    self.assertEqual(service.resolve_service(root/'Surface Studio.exe'),desktop.URL)
                with patch.object(service_discovery,'bind_server',side_effect=lambda handler,preferred:original(handler,port)),patch.object(desktop,'open_window',side_effect=open_window):
                    desktop.run_primary(None)
                self.assertFalse((data/'service.json').exists())
        finally:
            desktop.URL=old_url
            for name,value in saved.items():setattr(app,name,value)

if __name__=='__main__':unittest.main()
