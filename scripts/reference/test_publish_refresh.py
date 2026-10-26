"""Real local Git remote tests; gh auth/PR transport is explicitly mocked."""
import contextlib, hashlib, io, json, os, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from compile_usda import compile_index, compact_details
from test_compile_usda import raw, STAMP
from publish_refresh import publish, resume
from verify_index import verify

class PublicationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.old=Path.cwd();self.addCleanup(os.chdir,self.old)
  base=Path(self.temp.name);self.remote=base/'remote.git';self.repo=base/'work';self.repo.mkdir()
  self.run_git('init','--bare',str(self.remote),cwd=base)
  os.chdir(self.repo);self.run_git('init','-b','main');self.run_git('config','user.name','Fixture');self.run_git('config','user.email','fixture@example.test')
  self.run_git('remote','add','origin',str(self.remote));self.root=Path('public/reference');self.root.mkdir(parents=True)
  payload,_=compile_index([raw()],STAMP,'2025-10','https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2025-10-31.zip')
  shards=compact_details(payload)
  for path,value in shards.items():
   file=Path('public'+path);file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(value))
  data=json.dumps(payload).encode();(self.root/'products.json').write_bytes(data)
  (self.root/'build-report.json').write_text(json.dumps({'products':1,'sha256':hashlib.sha256(data).hexdigest()}))
  with contextlib.redirect_stdout(io.StringIO()):verify()
  self.run_git('add','.');self.run_git('commit','-m','baseline');self.run_git('push','origin','main')
  self.real_run=subprocess.run;self.gh=[];self.fail_pr=False
  def transport(args,**kw):
   if args[0]=='gh':
    self.gh.append(args)
    if self.fail_pr and args[1]=='pr':raise subprocess.CalledProcessError(1,args)
    return subprocess.CompletedProcess(args,0)
   return self.real_run(args,**kw)
  self.patch=patch('subprocess.run',side_effect=transport);self.patch.start();self.addCleanup(self.patch.stop)
 def run_git(self,*args,**kw):
  return subprocess.run(['git',*args],check=True,capture_output=True,text=True,**kw).stdout.strip()
 def invoke(self):
  with contextlib.redirect_stdout(io.StringIO()):return publish()
 def test_unchanged_does_not_authenticate_or_push(self):
  self.assertFalse(self.invoke());self.assertEqual(self.gh,[])
 def test_new_files_publish_with_only_reference_scope(self):
  (self.root/'new-public-metadata.json').write_text('{}');Path('private-note.txt').write_text('must stay local')
  self.assertTrue(self.invoke())
  files=self.run_git('--git-dir='+str(self.remote),'ls-tree','-r','--name-only','reference-refresh')
  self.assertIn('new-public-metadata.json',files);self.assertNotIn('private-note',files)
  self.assertTrue(any(args[1:3]==['pr','create'] for args in self.gh))
 def test_existing_review_branch_is_not_overwritten(self):
  self.run_git('push','origin','main:reference-refresh');before=self.run_git('rev-parse','HEAD')
  (self.root/'new.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'existing'):self.invoke()
  self.assertEqual(self.run_git('--git-dir='+str(self.remote),'rev-parse','reference-refresh'),before);self.assertEqual(self.gh,[])
 def test_invalid_index_does_not_push(self):
  (self.root/'products.json').write_text('{}')
  with self.assertRaises((KeyError,AssertionError)):self.invoke()
  self.assertEqual(self.run_git('ls-remote','--heads','origin','refs/heads/reference-refresh'),'')
 def test_unrelated_staged_data_blocks_publication(self):
  (self.root/'new.json').write_text('{}');Path('private-note.txt').write_text('private');self.run_git('add','private-note.txt')
  with self.assertRaisesRegex(ValueError,'Unrelated'):self.invoke()
  self.assertEqual(self.gh,[])
 def test_pr_failure_preserves_pushed_recovery_branch(self):
  (self.root/'new.json').write_text('{}');self.fail_pr=True
  with self.assertRaises(subprocess.CalledProcessError):self.invoke()
  self.assertTrue(self.run_git('ls-remote','--heads','origin','refs/heads/reference-refresh'))
 def test_coverage_uses_actual_release_not_april_2026(self):
  report=json.loads((self.root/'coverage-report.json').read_text());self.assertEqual(report['datasetDate'],'2025-10')
 def test_resume_validates_saved_branch_without_rewriting_it(self):
  (self.root/'new.json').write_text('{}');self.assertTrue(self.invoke());saved=self.run_git('rev-parse','HEAD');self.run_git('checkout','main');self.gh=[]
  with contextlib.redirect_stdout(io.StringIO()):self.assertTrue(resume())
  self.assertEqual(self.run_git('--git-dir='+str(self.remote),'rev-parse','reference-refresh'),saved)
  self.assertEqual(self.run_git('branch','--show-current'),'main')
  self.assertEqual(len(self.gh),1)
 def test_resume_rejects_branch_with_nonreference_changes(self):
  self.run_git('checkout','-b','reference-refresh');Path('private-note.txt').write_text('not public');self.run_git('add','.');self.run_git('commit','-m','bad branch');self.run_git('push','origin','reference-refresh');self.run_git('checkout','main')
  with self.assertRaisesRegex(ValueError,'non-reference'):resume()
  self.assertEqual(self.gh,[])
 def test_resume_refuses_a_dirty_checkout(self):
  Path('private-note.txt').write_text('local')
  with self.assertRaisesRegex(ValueError,'clean checkout'):resume()
  self.assertEqual(self.gh,[])
if __name__=='__main__':unittest.main()
