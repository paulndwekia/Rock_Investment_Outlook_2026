# Data governance and public-repository safeguards

## Before publishing research data

This repository is public. A dataset being accessible for research or download does not automatically grant permission to republish the original file, reproduce it in a public dashboard, or distribute derived extracts.

Before a source dataset is displayed or redistributed, record and verify:

- The data owner and exact source/product.
- The applicable licence or written permission.
- Whether permission covers private analysis, academic use, public display, redistribution and derived outputs.
- Required attribution, update frequency and any restrictions.
- The observation period, download date and file checksum.

Keep the approval record with the dataset in private project administration. Do not place credentials, session files or private approval correspondence in this repository.

## Files to keep out of Git

Keep downloaded source exports, canonical source workbooks, archives, browser captures, raw extracts and local database files in private storage. The root `.gitignore` now excludes the standard working directories for these files.

The CSV/XLSX ingestion service accepts a local file and a permission reference. Its `--approved-for-display` option is a deliberate confirmation step; it does not verify a licence or contact the data owner.

## Existing repository history

Adding a `.gitignore` rule does not remove files that Git already tracks. Deleting a file in a later commit also does not remove the earlier copies from Git history.

Before a public production deployment, review the existing repository tree and commit history for source exports and derived files whose publication rights are not confirmed. If any material must be withdrawn, first create a secure backup and agree on the cleanup plan. Removing historical copies requires a coordinated Git-history rewrite and force-push; coordinate with anyone who has cloned the repository because their local history will need to be reconciled.

Do not rewrite history or remove existing research files automatically. Confirm the relevant permissions and the intended retention policy first.

## Production rule

Only import and publish observations whose source permissions expressly cover the intended use. Keep raw source data private where public display is not authorised, and publish only approved outputs with clear provenance and methodology.
