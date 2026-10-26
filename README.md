# FlavorQuest public reference index

Public USDA FoodData Central beverage references and reproducible compiler. No personal collection records are included.

Source: https://fdc.nal.usda.gov/download-datasets/ (USDA public-domain/CC0 data). See public/reference/build-report.json and coverage-report.json for source identity, counts and limitations. Product rows are source records, not promises of current availability or distinct formulations.

Run `python3 -m unittest discover -s scripts/reference -p 'test_*.py'` and `python3 scripts/reference/verify_index.py` to verify.

The refresh workflow uses a standard public Ubuntu runner, no artifacts or caches, and no paid services. It runs on relevant code pushes, manual dispatch and monthly on the third day at 09:17 UTC. Scheduled jobs may be delayed or disabled. Changes prepare a review branch and do not deploy Explorer. Existing review branches are not overwritten. This repository contains no private application data or credentials.

## Publication verification

Forced official-source rebuild run 40253332821 rebuilt and validated 10,709 records and 32 shards and pushed `reference-refresh`. Repository policy blocked Actions pull-request creation. The repository owner must enable **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** before automatic PR creation can work. No automatic approval, merge or private application deployment is configured. The saved review branch is retained; do not force-overwrite it. Current Python suite: 27 passing tests.

### Superseding result

The PR permission blocker is resolved: hosted run 40254148286 passed 30 tests, verified 10,709 products and 32 shards, and created https://github.com/jordan61-dot/FlavorQuest/pull/1. Safe resume validates the saved reference-only branch without overwriting it. No automatic merge or private application deployment occurs.
