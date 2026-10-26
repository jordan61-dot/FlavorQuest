#!/usr/bin/env python3
"""Stage and verify a USDA snapshot, then swap directories with rollback.
Accepts a deliberately supplied, licensed source archive. Does not download,
change personal records, schedule jobs, or publish unverified data.
"""
import argparse, os, subprocess, sys, tempfile
from pathlib import Path
from verify_index import verify
from compile_usda import SOURCE_URL

def promote(staged, target, previous=None):
    staged,target=Path(staged),Path(target)
    verify(staged)  # failure must happen before existing snapshot is moved
    previous=Path(previous) if previous else target.with_name(target.name+'.previous')
    previous.parent.mkdir(parents=True,exist_ok=True)
    if previous.exists():raise ValueError('Previous snapshot exists; review it before refreshing again.')
    moved=False
    try:
        if target.exists():os.replace(target,previous);moved=True
        os.replace(staged,target)
    except BaseException:
        if moved and not target.exists():os.replace(previous,target)
        raise
    return previous if moved else None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,default=Path('public/reference'));p.add_argument('--source-url',default=SOURCE_URL);a=p.parse_args()
    if not a.archive.is_file():p.error('Supply an existing public USDA ZIP archive.')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    # Same filesystem as target permits atomic individual directory renames.
    with tempfile.TemporaryDirectory(prefix='reference-stage-',dir=a.output.parent) as temp:
        stage=Path(temp)/'reference'
        subprocess.run([sys.executable,str(Path(__file__).with_name('compile_usda.py')),str(a.archive),'--output',str(stage/'products.json'),'--source-url',a.source_url],check=True)
        previous=promote(stage,a.output,Path('.reference-history')/a.output.name)
        print('Verified snapshot installed. Prior snapshot retained at:',previous)
    print('Review the source diff, run application tests/build, then publish through the established Site workflow. No publication or schedule is claimed.')
if __name__=='__main__':main()
