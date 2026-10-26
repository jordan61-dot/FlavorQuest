"""Deterministic integrity tests; no live downloads or personal databases."""
import unittest
from compile_usda import compile_index, eligible, record, identity, clean_name, compact_details

STAMP='2026-10-24T22:40:00Z'
def raw(identifier=1,**updates):
    return dict(fdcId=identifier,description='EXAMPLE, ROOT BEER',brandName='EXAMPLE',brandOwner='EXAMPLE COMPANY',brandedFoodCategory='Soda',marketCountry='United States',modifiedDate='4/30/2026',ingredients='WATER, SUGAR',**updates)
class CompilerTests(unittest.TestCase):
    def test_foods_and_concentrates_are_not_drinks(self):
        for name in ['Root Beer Candy','ROOT BEER SYRUP','ORANGE SODA DRINK MIX','COLA POWDER','GINGER BEER CONCENTRATE']:
            r=raw();r['description']=name;self.assertFalse(eligible(r))
    def test_source_identity_market_and_ingredients_preserved(self):
        r=record(raw(),{'example':'EXAMPLE'},STAMP)
        self.assertEqual(r['ingredients'],'WATER, SUGAR');self.assertEqual(r['market'],'United States')
        self.assertNotIn('origin',r);self.assertNotIn('manufacturer',r);self.assertNotIn('rating',r)
        self.assertEqual(r['source'],'https://fdc.nal.usda.gov/food-details/1/nutrients')
    def test_packages_collapse_and_latest_record_wins(self):
        a=raw();a['description']='Example Root Beer 12 fl oz';a['modifiedDate']='4/1/2020'
        b=raw(2);b['description']='Example Root Beer 20 fl oz'
        p,s=compile_index([a,b],STAMP)
        self.assertEqual(s['products'],1);self.assertEqual(p['products'][0]['id'],'usda:2')
    def test_diet_zero_and_cane_sugar_remain_distinct(self):
        rows=[]
        for i,name in enumerate(['Root Beer','Diet Root Beer','Zero Sugar Root Beer','Cane Sugar Root Beer']):
            r=raw(i+1);r['description']=name;rows.append(r)
        p,_=compile_index(rows,STAMP);self.assertEqual(len(p['products']),4)
    def test_owner_is_not_asserted_as_manufacturer(self):
        r=raw();r.pop('brandName');item=record(r,{},STAMP)
        self.assertEqual(item['brandBasis'],'brandOwner (brand unreported)')
        self.assertIn('Brand unreported',item['description']);self.assertNotIn('manufacturer',item)
    def test_prefix_brand_requires_source_evidence(self):
        r=raw();r.pop('brandName');r['description']='FROSTIE, ROOT BEER'
        item=record(r,{'frostie':'FROSTIE'},STAMP);self.assertEqual(item['brand'],'Frostie')
    def test_deterministic_generation_independent_of_input_order(self):
        a=raw();b=raw(2);b['description']='Example Orange Soda'
        self.assertEqual(compile_index([a,b],STAMP),compile_index([b,a],STAMP))
    def test_packaging_words_do_not_create_new_drinks(self):
        a=raw();a['description']='Example Root Beer Bottle'
        b=raw(2);b['description']='Example Root Beer Can'
        p,s=compile_index([a,b],STAMP);self.assertEqual(s['products'],1)
        self.assertEqual(clean_name('ROOT BEER SODA, ROOT BEER'),'Root Beer Soda')
    def test_ambiguous_generic_brand_records_are_skipped(self):
        for name in ('Gourmet Soda','Example Soft Drink','Non Alcoholic Beverage'):
            a=raw();a['description']=name;self.assertIsNone(record(a,{},STAMP))

    def test_lazy_details_keep_all_source_fields_and_stable_links(self):
        payload,_=compile_index([raw(),raw(2)],STAMP)
        original=payload['products'][0].copy()
        shards=compact_details(payload)
        self.assertNotIn('ingredients',payload['products'][0])
        path=payload['products'][0]['detailPath']
        self.assertRegex(path,r'^/reference/details/usda-\d{2}\.json$')
        details=shards[path]['products'][0]
        self.assertEqual(details['id'],original['id'])
        for key in ('ingredients','brandOwner','sourceModified','brandBasis'):
            self.assertEqual(details[key],original[key])
        self.assertEqual(shards[path]['source'],payload['source'])

    def test_missing_brand_and_owner_are_rejected(self):
        r=raw();r.pop('brandName');r.pop('brandOwner')
        self.assertIsNone(record(r,{},STAMP))

    def test_no_unknown_values_fabricated(self):
        r=raw();r.pop('modifiedDate');r.pop('ingredients');r.pop('marketCountry')
        item=record(r,{'example':'Example'},STAMP)
        for field in ['ingredients','sourceModified','market','origin','release','history','rating','image']:
            self.assertNotIn(field,item)
if __name__=='__main__':unittest.main()
