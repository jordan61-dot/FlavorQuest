import unittest
from download_refresh import latest
class DownloadTests(unittest.TestCase):
 def test_selects_latest_valid_release_from_official_links(self):
  text='<a href="/fdc-datasets/FoodData_Central_branded_food_json_2025-04-30.zip">older</a><a href="https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip">latest</a>'
  self.assertTrue(latest(text).endswith('2026-04-30.zip'))
 def test_rejects_unrelated_lookalike_and_future_urls(self):
  for link in ['https://evil.test/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip','https://fdc.nal.usda.gov.evil.test/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip','/fdc-datasets/FoodData_Central_branded_food_json_2099-04-30.zip','/other.zip']:
   with self.assertRaises(ValueError):latest('<a href="'+link+'">x</a>')
 def test_rejects_missing_links(self):
  with self.assertRaises(ValueError):latest('<html>source unavailable</html>')

class SourceMetadataTests(unittest.TestCase):
 def test_compiler_labels_the_actual_release(self):
  from compile_usda import compile_index
  payload,_=compile_index([], '2026-10-25T00:00:00Z','2025-10','https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2025-10-31.zip')
  self.assertEqual(payload['source']['id'],'usda-fdc-branded-2025-10')
  self.assertEqual(payload['source']['datasetDate'],'2025-10')
  self.assertTrue(payload['source']['download'].endswith('2025-10-31.zip'))

if __name__=='__main__':unittest.main()
