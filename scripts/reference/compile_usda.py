#!/usr/bin/env python3
"""Compile a bounded, public-domain beverage reference snapshot from USDA's bulk ZIP.

Streams source records; never downloads or processes the bulk dataset on the user's
phone. Only public product metadata is emitted. No personal/availability inference.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, unicodedata, zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = 'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip'
MAX_BYTES = 4 * 1024 * 1024
MAX_PRODUCTS = 20000
MAX_DETAIL_BYTES = 512 * 1024
DETAIL_SHARDS = 32
STYLES = ('root beer', 'birch beer', 'ginger beer', 'ginger ale', 'spruce beer', 'sarsaparilla', 'cream soda', 'orange soda', 'grape soda', 'grapefruit soda', 'cola', 'tonic water', 'sparkling water', 'seltzer', 'lemonade')
EXCLUDE = re.compile(r'\b(syrup|concentrate|powder|candy|candies|gummies|jelly|ice cream|frozen|cake|sauce|beef|pork|chicken|seasoning|drink mix|soda mix|water enhancer)\b', re.I)
RELEVANT = re.compile(r'\b(soda|soft drink|root beer|birch beer|ginger beer|ginger ale|spruce beer|sarsaparilla|cream soda|cola|sparkling|seltzer|lemonade|tonic water|energy drink|sports? drink)\b', re.I)
# Removing an explicit package volume/pack count does not invent a formulation.
PACKAGING = re.compile(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|floz|oz|oza|ml|liters?|litres?|litre|liter|l)\b|\b\d+\s*(?:pack|pk|ct|count|cans|bottles)\b', re.I)
FORMULATIONS = ('zero sugar', 'sugar free', 'diet', 'reduced sugar', 'cane sugar', 'real sugar', 'caffeine free')

def normal(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii','ignore').decode().lower().replace('&', ' and ')
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def title(text):
    text = re.sub(r'\s+', ' ', str(text)).strip()
    return text.title() if text.isupper() else text

def clean_name(text):
    text = PACKAGING.sub('', text)
    text = re.sub(r'\b(?:bottles?|cans?)\b', '', text, flags=re.I)
    chunks = [part.strip(' ,;-') for part in text.split(',')]
    # USDA often repeats the flavor at the end of its description.
    kept = []
    for part in chunks:
        if part and not any(re.search(r'(?<!\w)'+re.escape(normal(part))+r'(?!\w)',normal(x)) for x in kept): kept.append(part)
    return title(', '.join(kept)).strip(' ,;-')

def eligible(row):
    name = str(row.get('description', ''))
    category = str(row.get('brandedFoodCategory', '')).lower()
    if EXCLUDE.search(name): return False
    return category in ('soda', 'drinks - soft drinks') or (
        any(x in category for x in ('drink', 'beverage', 'water')) and bool(RELEVANT.search(name)))

def parse_date(text):
    if not isinstance(text,str): return ''
    for form in ('%m/%d/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(text,form).date().isoformat()
        except ValueError: pass
    return ''

def read_rows(path):
    """Current USDA bulk JSON is one complete food object per physical line.
    Reject changed framing rather than silently emitting a partial new schema.
    """
    decoder=json.JSONDecoder()
    with zipfile.ZipFile(path) as archive:
        names=[n for n in archive.namelist() if n.endswith('.json') and 'branded_food' in n]
        if len(names)!=1: raise ValueError('Expected one USDA branded-food JSON member.')
        with archive.open(names[0]) as source:
            start=source.readline().strip()
            if start != b'{"BrandedFoods": [': raise ValueError('USDA framing changed; review compiler before updating.')
            closed=False
            for raw in source:
                if not raw.strip(): continue
                line=raw.decode('utf-8').strip()
                if line in (']}', ']}\n'): closed=True;continue
                row,end=decoder.raw_decode(line)
                rest=line[end:].strip()
                if rest not in ('', ',', ']}'): raise ValueError('Unsupported USDA record framing.')
                if rest==']}':closed=True
                if not isinstance(row,dict) or row.get('foodClass')!='Branded': raise ValueError('Unexpected source record.')
                yield row
            if not closed: raise ValueError('Incomplete USDA source document.')

def choose_brand(row,known_brands):
    direct=str(row.get('brandName','')).strip()
    if direct:return title(direct),'brandName'
    raw=str(row.get('description',''));normalized_raw=normal(raw)
    prefix=raw.split(',')[0].strip()
    # A description prefix is used only if independently present as a brandName
    # in this same source dataset. Do not guess a brand from a generic flavor.
    if normal(prefix) in known_brands:return title(prefix),'description prefix + source brandName'
    matches=[(key,label) for key,label in known_brands.items() if len(key)>2 and normalized_raw.startswith(key+' ')]
    if matches:return title(max(matches,key=lambda x:len(x[0]))[1]),'description prefix + source brandName'
    owner=str(row.get('brandOwner','')).strip()
    return (title(owner),'brandOwner (brand unreported)') if owner else ('','unknown')

def record(row,known_brands,retrieved):
    name=clean_name(str(row.get('description','')))
    brand,basis=choose_brand(row,known_brands)
    fdc=row.get('fdcId')
    if not name or not brand or not isinstance(fdc,int) or fdc<=0:return None
    variant=normal(name)
    if variant.startswith(normal(brand)+' '):variant=variant[len(normal(brand))+1:]
    if variant in ('soda','soft drink','gourmet soda','carbonated beverage','non alcoholic beverage','sparkling drink','beverage','drink'):return None
    # Display product identity, with owner fallback transparently labeled below.
    if normal(brand) not in normal(name):name=f'{brand} {name}'
    result={'id':f'usda:{fdc}','name':name,'brand':brand,
      'source':f'https://fdc.nal.usda.gov/food-details/{fdc}/nutrients',
      'retrieved':retrieved,'category':'Soft drink','brandBasis':basis}
    original=str(row.get('description','')).strip()
    if normal(original) not in normal(name):result['aliases']=[original]
    owner=str(row.get('brandOwner','')).strip()
    if owner:result['brandOwner']=owner
    modified=parse_date(row.get('modifiedDate')) or parse_date(row.get('publicationDate'))
    if modified:result['sourceModified']=modified
    if basis.startswith('brandOwner'):result['description']='Brand unreported; source brand owner shown as label. Confirm exact product.'
    category=str(row.get('brandedFoodCategory',''))
    if category not in ('Soda','Drinks - Soft Drinks'):result['category']=category
    low=normal(original)
    for style in STYLES:
        if style in low:result['style']=title(style);break
    for formulation in FORMULATIONS:
        if formulation in low:result['formulation']=title(formulation);break
    ingredients=str(row.get('ingredients','')).strip()
    if ingredients:result['ingredients']=ingredients
    market=str(row.get('marketCountry','')).strip()
    if market:result['market']=market
    # marketCountry is distribution information, never origin or manufacture.
    return result

def identity(row):
    name=normal(row['name']);brand=normal(row['brand'])
    if name.startswith(brand+' '):name=name[len(brand)+1:]
    return brand+'|'+name+'|'+normal(row.get('formulation',''))

def compile_index(rows,retrieved,dataset_date='2026-04',source_url=SOURCE_URL):
    selected=[row for row in rows if eligible(row)]
    known={normal(row['brandName']):str(row['brandName']) for row in selected if row.get('brandName')}
    chosen={};eligible_count=len(selected);skipped=0
    for raw in selected:
        item=record(raw,known,retrieved)
        if item is None:skipped+=1;continue
        key=identity(item);old=chosen.get(key)
        # Keep latest source metadata, deterministic FDC id tie break.
        if old is None or (item.get('sourceModified',''),int(item['id'][5:]))>(old.get('sourceModified',''),int(old['id'][5:])):chosen[key]=item
    products=sorted(chosen.values(),key=lambda r:(normal(r['brand']),normal(r['name']),r['id']))
    if len(products)>MAX_PRODUCTS:raise ValueError('Index exceeds client row bound; review sharding.')
    payload={'formatVersion':1,'generatedAt':retrieved,
      'source':{'id':'usda-fdc-branded-'+dataset_date,'name':'USDA FoodData Central','url':'https://fdc.nal.usda.gov/download-datasets/','license':'CC0 1.0 / public domain','datasetDate':dataset_date,'download':source_url},
      'products':products}
    stats={'sourceRows':len(rows),'eligibleRows':eligible_count,'products':len(products),'skippedMissingIdentity':skipped,
       'brandLabels':len({r['brand'] for r in products}),'ownerFallbackProducts':sum(r['brandBasis'].startswith('brandOwner') for r in products),
       'rootBeerProducts':sum(normal(r.get('style',''))=='root beer' for r in products)}
    return payload,stats

def compact_details(payload):
    """Keep identity search lightweight; full label details are lazily fetched on review."""
    shards={}
    for product in payload['products']:
        details={'id':product['id']}
        for key in ('ingredients','brandOwner','sourceModified','brandBasis'):
            if key in product:details[key]=product.pop(key)
        index=int(product['id'][5:]) % DETAIL_SHARDS
        path=f'/reference/details/usda-{index:02d}.json'
        product['detailPath']=path
        shards.setdefault(path,{'formatVersion':1,'generatedAt':payload['generatedAt'],
            'source':payload['source'],'products':[]})['products'].append(details)
    return shards

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,default=Path('public/reference/products.json'))
    parser.add_argument('--retrieved-at',default=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
    parser.add_argument('--source-url',default=SOURCE_URL)
    args=parser.parse_args()
    match=re.fullmatch(r'https://fdc\.nal\.usda\.gov/fdc-datasets/FoodData_Central_branded_food_json_(\d{4}-\d{2}-\d{2})\.zip',args.source_url)
    if not match:parser.error('Unsupported USDA source URL.')
    datetime.strptime(match[1],'%Y-%m-%d')
    dataset_date=match[1][:7]
    # Retain only candidate beverage objects; discard nutrient arrays immediately.
    count=0;rows=[]
    for row in read_rows(args.archive):
        count+=1
        if eligible(row):rows.append({k:v for k,v in row.items() if k in ('fdcId','description','brandName','brandOwner','ingredients','marketCountry','brandedFoodCategory','modifiedDate','publicationDate')})
    payload,stats=compile_index(rows,args.retrieved_at,dataset_date,args.source_url);stats['sourceRows']=count
    shards=compact_details(payload)
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    encoded_shards={path:json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8') for path,value in shards.items()}
    if any(len(value)>MAX_DETAIL_BYTES for value in encoded_shards.values()):raise ValueError('Detail shard exceeds512KiB; increase deterministic shard count.')
    if len(encoded)>MAX_BYTES:raise ValueError(f'Index is {len(encoded)} bytes, over 4MiB; review sharding, do not silently drop rows.')
    args.output.parent.mkdir(parents=True,exist_ok=True);temp=args.output.with_suffix('.tmp');temp.write_bytes(encoded);temp.replace(args.output)
    for path,value in encoded_shards.items():
        target=args.output.parent/'details'/Path(path).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
    with args.archive.open('rb') as source: archive_hash=hashlib.file_digest(source,'sha256').hexdigest()
    stats.update({'sourceArchiveSha256':archive_hash,'detailShards':len(shards),'detailBytes':sum(len(v) for v in encoded_shards.values()),'maxDetailBytes':max(map(len,encoded_shards.values()),default=0),'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest(),'generatedAt':args.retrieved_at,'datasetDate':dataset_date})
    args.output.with_name('build-report.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
