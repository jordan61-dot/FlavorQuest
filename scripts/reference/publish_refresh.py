#!/usr/bin/env python3
"""Publish only validated public reference changes to a non-overwriting review branch."""
import subprocess
from verify_index import verify
BRANCH='reference-refresh'
def git(*args):
 return subprocess.run(['git',*args],check=True,capture_output=True,text=True).stdout.strip()
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
 try:
  subprocess.run(['gh','pr','create','--base','main','--head',BRANCH,'--title','Review validated beverage reference refresh','--body','Public source metadata only. Validation passed. Review before importing into Explorer; no personal data or automatic application deployment is included.'],check=True)
 except subprocess.CalledProcessError:
  print('Reference branch was saved. Pull request creation failed; open a PR from reference-refresh to main. No application deployment occurred.')
  raise
 return True
if __name__=='__main__':publish()
