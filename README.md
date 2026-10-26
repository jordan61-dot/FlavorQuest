# FlavorQuest public reference index

Public USDA FoodData Central beverage references and reproducible compiler. No personal collection records are included.

Source: https://fdc.nal.usda.gov/download-datasets/ (USDA public-domain/CC0 data). See public/reference/build-report.json and coverage-report.json for source identity, counts and limitations. Product rows are source records, not promises of current availability or distinct formulations.

Run `python3 -m unittest discover -s scripts/reference -p 'test_*.py'` and `python3 scripts/reference/verify_index.py` to verify.

The refresh workflow uses a standard public Ubuntu runner, no artifacts or caches, and no paid services. It runs on relevant code pushes, manual dispatch and monthly on the third day at 09:17 UTC. Scheduled jobs may be delayed or disabled. Changes prepare a review branch and do not deploy Explorer. Existing review branches are not overwritten. This repository contains no private application data or credentials.
