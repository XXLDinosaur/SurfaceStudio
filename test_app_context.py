import unittest
from app_context import ApplicationContext
class ContextTests(unittest.TestCase):
 def test_instances_do_not_share_state_or_locks(self):
  a,b=ApplicationContext(),ApplicationContext();a.CONFIG['root']='first'
  self.assertEqual(b.CONFIG,{})
  self.assertIsNot(a.LOCK,b.LOCK)
 def test_consumer_sees_replaced_state(self):
  a=ApplicationContext();consumer=a;a.ASSETS={'old':{}};a.ASSETS={'new':{}}
  self.assertEqual(list(consumer.ASSETS),['new'])
if __name__=='__main__':unittest.main()
