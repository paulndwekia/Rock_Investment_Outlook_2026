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


## Targeted public-repository review — 18 November 2026

A review of the current public repository tree found source-origin workbooks and derived extracts still tracked under `data/canonical/`, `data/incoming/` and `analysis/`. Examples include the NSE workbook in `data/canonical/nse_analysis.xlsx`, the consolidated observations extract in `analysis/rock_flat_observations.csv`, and the cleaned NSE analysis file in `analysis/clean_nse_analysis.csv`.

The current `.gitignore` contains rules for these working directories, but those rules do not untrack files that have already been committed. Because this repository is public, these items are already accessible from its public GitHub history. Do not copy them into the new dashboard or a public backend until the data owner’s terms and permissions have been confirmed.

The source register also contains machine-local Windows archive paths. These are not access credentials, but they are unnecessary environment details and should be removed from any public provenance view. Preserve the original audit register in controlled private storage if it is needed for research reproducibility.

### Research report quality gate

The report generated on 03 October 2026 uses observations through 29 June 2026. The published report text contains non-finite results such as `inf%` and `nan%`, as well as an annualised volatility figure of `47,569,706.54%`. These results must not be presented as valid investment statistics. Re-run the security-level calculations with explicit handling for zero or invalid starting prices, duplicate/stale observations, corporate actions, missing returns and outliers; then independently reconcile the summary tables and chart inputs.

Until this work is complete:
- Do not reproduce those report statistics in the new dashboard, marketing material or email attachments.
- Treat the existing report as a historical working paper, not a validated current investment recommendation.
- Label each data series with its source, unit, observation date and calculation method.
- Refresh the data only through an authorised source-access route.

### Release status

The new Next.js dashboard deployment contains the dashboard application only. It does not publish the tracked source workbooks or the old research report and currently shows a no-data state. Its read-only data API and PostgreSQL store have not yet been configured.

Before a public, data-enabled launch:
1. Confirm Rock Data Plus permissions for public display, redistribution and derived outputs in writing.
2. Agree a secure retention plan for the already tracked raw files. If withdrawal is required, take a controlled backup and coordinate a Git-history rewrite and force-push; do not simply delete files in a new commit and assume the historical copies are gone.
3. Recompute and validate the report’s non-finite and extreme outputs.
4. Provision a database and deploy the protected ingestion/API service in an explicitly selected hosting workspace.
5. Configure the frontend’s server-side API URL and read token, then verify the production data path end-to-end.

No source files have been removed and no Git history has been rewritten as part of this review.
