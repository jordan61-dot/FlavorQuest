import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from refresh_index import promote

class RefreshTests(unittest.TestCase):
 def test_invalid_stage_preserves_current_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'reference';target.mkdir();(target/'keep').write_text('exact old content');stage=Path(d)/'stage';stage.mkdir()
   with patch('refresh_index.verify',side_effect=ValueError('invalid')):
    with self.assertRaises(ValueError):promote(stage,target)
   self.assertEqual((target/'keep').read_text(),'exact old content')
 def test_success_retains_restorable_previous_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'reference';target.mkdir();(target/'value').write_text('old');stage=Path(d)/'stage';stage.mkdir();(stage/'value').write_text('new')
   with patch('refresh_index.verify'):previous=promote(stage,target)
   self.assertEqual((target/'value').read_text(),'new');self.assertEqual((previous/'value').read_text(),'old')
 def test_interrupted_promotion_rolls_back(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   target=Path(d)/'reference';target.mkdir();(target/'value').write_text('old');stage=Path(d)/'stage';stage.mkdir();real=os.replace
   def fail(src,dst):
    if Path(src)==stage:raise OSError('simulated write failure')
    return real(src,dst)
   with patch('refresh_index.verify'),patch('refresh_index.os.replace',side_effect=fail):
    with self.assertRaises(OSError):promote(stage,target)
   self.assertEqual((target/'value').read_text(),'old')
if __name__=='__main__':unittest.main()
