#!/usr/bin/env python3
"""Verify generated public index/shard integrity without touching personal records."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
from compile_usda import normal,MAX_BYTES,MAX_PRODUCTS,MAX_DETAIL_BYTES

def verify(root=Path('public/reference')):
    raw=(root/'products.json').read_bytes();index=json.loads(raw)
    assert len(raw)<=MAX_BYTES and index['formatVersion']==1
    products=index['products'];assert 0<len(products)<=MAX_PRODUCTS
    assert len({p['id'] for p in products})==len(products)
    report=json.loads((root/'build-report.json').read_text())
    assert report['products']==len(products) and report['sha256']==hashlib.sha256(raw).hexdigest()
    details={};seen=set()
    for file in sorted((root/'details').glob('*.json')):
        data=file.read_bytes();assert len(data)<=MAX_DETAIL_BYTES
        shard=json.loads(data);assert shard['formatVersion']==1 and shard['source']==index['source'] and shard['generatedAt']==index['generatedAt']
        assert len(shard['products'])<=2000
        for item in shard['products']:
            assert item['id'] not in seen;seen.add(item['id']);details[item['id']]=(file.name,item)
    assert seen=={p['id'] for p in products}
    forbidden={'rating','tried','needsRetaste','acquisition','quantity','origin','manufacturer','release','history'}
    for p in products:
        assert not forbidden.intersection(p)
        assert re.fullmatch(r'usda:\d+',p['id'])
        assert p['source']==f"https://fdc.nal.usda.gov/food-details/{p['id'][5:]}/nutrients"
        assert p['detailPath']=='/reference/details/'+details[p['id']][0]
        assert p['brand'] and p['name']
    queries={}
    for query in ['root beer','Fanta','Ale-8-One','Sioux City','Sprecher','Frostie','Nehi','Bundaberg']:
        if query=='root beer':rows=[p for p in products if normal(query) in normal(p['name']+' '+p.get('style',''))]
        else:rows=[p for p in products if normal(p['brand'])==normal(query) or normal(p['brand']).startswith(normal(query)+' ')]
        queries[query]={'records':len(rows),'brandOrOwnerLabels':len({normal(p['brand']) for p in rows}),
            'examples':[{'id':p['id'],'name':p['name'],'source':p['source']} for p in rows[:8]]}
    coverage={'description':'Normalized source identity records, not independently verified unique formulations or current availability. Residual wording and manufacturer-label duplicates may remain.',
       'generatedAt':index['generatedAt'],'datasetDate':'2026-04','queries':queries}
    (root/'coverage-report.json').write_text(json.dumps(coverage,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'verifiedProducts':len(products),'verifiedShards':len(list((root/'details').glob('*.json'))),'rootBeerRecords':queries['root beer']['records'],'rootBeerBrandOrOwnerLabels':queries['root beer']['brandOrOwnerLabels'],'queries':{q:v['records'] for q,v in queries.items()}},indent=2))
if __name__=='__main__':verify()
