import json
from pathlib import Path
import tempfile
import time
import unittest
import uuid
from blender_bridge import BlenderBridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.bridge=BlenderBridge(Path(self.temp.name))
        self.sid=uuid.uuid4().hex
        self.session={'id':self.sid,'heartbeat':time.time(),'objects':[{'name':'Cube','key':'1'}],
                      'mode':'OBJECT','revision':'revision-1','busy':False}
        self.bridge.write(self.bridge.root/'sessions'/(self.sid+'.json'),self.session)

    def tearDown(self): self.temp.cleanup()

    def enqueue(self, **kwargs):
        return self.bridge.enqueue(self.sid,{'id':'material','maps':[]},kwargs.get('options',{}),kwargs.get('revision','revision-1'))

    def test_expired_sessions_are_offline(self):
        self.session['heartbeat']=time.time()-20
        self.bridge.write(self.bridge.root/'sessions'/(self.sid+'.json'),self.session)
        self.assertEqual(self.bridge.sessions(),[])
        with self.assertRaises(ValueError): self.enqueue()

    def test_stale_selection_is_rejected(self):
        with self.assertRaises(ValueError): self.enqueue(revision='old-selection')

    def test_duplicate_requests_are_rejected(self):
        self.enqueue()
        with self.assertRaises(ValueError): self.enqueue()

    def test_job_and_acknowledgment_roundtrip(self):
        queued=self.enqueue(options={'repeat':3,'flipNormalY':True})
        job=self.bridge.read(self.bridge.root/'requests'/(self.sid+'.json'))
        self.assertEqual(job['options']['repeat'],3)
        self.assertTrue(job['options']['flipNormalY'])
        self.assertEqual(self.bridge.result(queued['id'])['status'],'pending')
        self.bridge.write(self.bridge.root/'results'/(queued['id']+'.json'),{'status':'success','id':queued['id']})
        self.assertEqual(self.bridge.result(queued['id'])['status'],'success')

    def test_invalid_tiling_and_traversal_rejected(self):
        for value in [-1,0,101,float('nan'),float('inf')]:
            with self.assertRaises(ValueError): self.enqueue(options={'repeat':value})
        with self.assertRaises(ValueError): self.bridge.result('../state')

    def test_edit_mode_requires_faces(self):
        self.session.update(mode='EDIT_MESH',selectedFaces=0)
        self.bridge.write(self.bridge.root/'sessions'/(self.sid+'.json'),self.session)
        with self.assertRaises(ValueError): self.enqueue()


if __name__=='__main__': unittest.main(verbosity=2)
