#!/usr/bin/env python3
"""Publish only validated public reference changes to a non-overwriting review branch."""
import argparse, subprocess, tempfile
from pathlib import Path
from verify_index import verify
BRANCH='reference-refresh'
def git(*args):
 return subprocess.run(['git',*args],check=True,capture_output=True,text=True).stdout.strip()
def resume():
 # Recover the saved branch using the SAME Actions credentials and permissions.
 if git('status','--porcelain'):
  raise ValueError('Resume requires a clean checkout.')
 if git('rev-parse','--is-shallow-repository')=='true':git('fetch','--unshallow','origin')
 git('fetch','origin','main')
 git('fetch','origin',BRANCH)
 saved=git('rev-parse','FETCH_HEAD')
 base=git('merge-base','origin/main',saved)
 paths=git('diff','--name-only',base,saved).splitlines()
 if not paths or any(not p.startswith('public/reference/') for p in paths):
  raise ValueError('Saved branch is empty or contains non-reference changes.')
 with tempfile.TemporaryDirectory() as folder:
  checkout=Path(folder)/'review'
  git('worktree','add','--detach',str(checkout),saved)
  try:verify(checkout/'public/reference')
  finally:git('worktree','remove','--force',str(checkout))
 # Do not rewrite any branch or bypass a denied PR permission.
 create_review()
 return True

def create_review():
 try:
  subprocess.run(['gh','pr','create','--base','main','--head',BRANCH,'--title','Review validated beverage reference refresh','--body','Public source metadata only. Validation passed. Review before importing into Explorer; no personal data or automatic application deployment is included.'],check=True)
 except subprocess.CalledProcessError:
  print('Reference branch was saved. Pull request creation failed; enable repository Actions PR permission or open a PR manually. No application deployment occurred.')
  raise

def publish():
 verify()
 if not git('status','--porcelain','--','public/reference'):
  print('Public reference source unchanged.');return False
 # A staged unrelated file must never leak into the reference commit.
 staged=git('diff','--cached','--name-only').splitlines()
 if any(not p.startswith('public/reference/') for p in staged):
  raise ValueError('Unrelated staged files found; refusing publication.')
 if git('ls-remote','--heads','origin','refs/heads/'+BRANCH):
  raise ValueError('An existing reference-refresh branch needs review; nothing was overwritten.')
 subprocess.run(['gh','auth','setup-git'],check=True)
 git('checkout','-b',BRANCH)
 git('add','--','public/reference')
 git('-c','user.name=Reference update workflow','-c','user.email=reference-update@users.noreply.github.com','commit','-m','Prepare validated public beverage references')
 # Fast-forward-only push; a concurrent branch change cannot be overwritten.
 git('push','origin',BRANCH)
 create_review()
 return True
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
 resume() if args.resume else publish()
