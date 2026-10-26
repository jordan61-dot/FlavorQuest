#!/usr/bin/env python3
"""Fail-closed official USDA release downloader; no private data or credentials."""
import argparse, hashlib, html, json, re, subprocess, sys, tempfile, urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
LISTING='https://fdc.nal.usda.gov/download-datasets/'
PATTERN=r'https://fdc\.nal\.usda\.gov/fdc-datasets/FoodData_Central_branded_food_json_(\d{4}-\d{2}-\d{2})\.zip'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Source redirect rejected; review official endpoint.')
def latest(text):
 urls=[]
 for path in re.findall(r'href=[\"\']([^\"\']+)[\"\']',text,re.I):
  url=urljoin(LISTING,html.unescape(path));m=re.fullmatch(PATTERN,url)
  if m and date.fromisoformat(m[1])<=date.today():urls.append(url)
 if not urls:raise ValueError('No supported public branded-food release found; retain current index.')
 return max(set(urls))
def fetch(url,output=None,limit=2*1024*1024):
 opener=urllib.request.build_opener(NoRedirect)
 with opener.open(urllib.request.Request(url,headers={'User-Agent':'Explorer-reference-refresh/0.6.2'}),timeout=60) as response:
  total=0;chunks=[];digest=hashlib.sha256()
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   total+=len(chunk)
   if total>limit:raise ValueError('Public source exceeds download limit.')
   digest.update(chunk)
   if output:output.write(chunk)
   else:chunks.append(chunk)
 return digest.hexdigest() if output else b''.join(chunks).decode('utf-8')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('public/reference'));p.add_argument('--check-only',action='store_true');a=p.parse_args()
 url=latest(fetch(LISTING));print('Supported official source:',url)
 if a.check_only:return
 with tempfile.TemporaryDirectory() as temp:
  archive=Path(temp)/'source.zip'
  with archive.open('wb') as out:checksum=fetch(url,out,512*1024*1024)
  report=a.output/'build-report.json'
  if report.exists() and json.loads(report.read_text()).get('sourceArchiveSha256')==checksum:print('Unchanged source archive. No refresh or publication needed.');return
  subprocess.run([sys.executable,str(Path(__file__).with_name('refresh_index.py')),str(archive),'--output',str(a.output),'--source-url',url],check=True)
if __name__=='__main__':main()
