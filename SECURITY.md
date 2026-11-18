# Security and data-handling policy

## Scope

This repository contains a financial research project that has used Rock Data Plus exports. The source provider's records must be treated as restricted unless the applicable written terms expressly permit the specific use and public display.

## Do not commit

- Raw Rock Data Plus CSV, Excel, database or browser-capture files.
- Database backups, local SQLite files, WAL/SHM files or private research extracts.
- API tokens, passwords, OAuth credentials, connection strings or environment files.
- Personal data or local computer paths embedded in operational logs and manifests.

Keep source exports and working databases in private storage. Use a separately reviewed, permission-cleared public dataset when building public dashboard examples.

## Important: ignore rules do not remove tracked history

The `.gitignore` patterns prevent matching *untracked* files from being added in future commits. They do not untrack files already committed, remove earlier versions from Git history, or revoke access to previously cloned or forked copies.

A repository visibility change also does not replace a data-retention or licensing review.

## Repository incident / cleanup procedure

1. Temporarily change the source repository to **Private** in GitHub Settings → General → Danger Zone → Change repository visibility.
2. Preserve a verified backup of the repository and the source files in private storage before deleting or rewriting anything.
3. Review the full Git history, not only the current branch tree, for source exports, local databases, tokens and personal metadata.
4. Coordinate a history rewrite (for example with `git filter-repo`) from a verified backup, remove restricted paths from every affected branch and tag, and force-push only after collaborators are informed.
5. Revoke and rotate any credential that may have been committed. Removing a credential from the latest tree is not enough.
6. Verify that no restricted source exports remain in the cleaned public repository before changing its visibility back to Public.
7. Keep a private archival copy and document the data-owner permission that supports each dataset intended for public display.

History rewriting changes commit IDs and can disrupt open pull requests, branches and local clones. Do not run it without a verified backup and a coordinated maintenance plan.

## Dashboard publication rules

- The public dashboard must not connect to a private local SQLite database or expose database credentials.
- Only publish records and derived outputs that are approved for the intended audience and display method.
- Preserve source, observation date, unit, transformation and licence/provenance metadata for published series.
- Keep the public dashboard in an explicit empty state until an authorised data feed is configured.
- Never replace missing data with generated market observations or invented investment statistics.

## Reporting

For a suspected disclosure or security issue, stop further publication and review the repository visibility, affected commits, collaborators, forks and any exposed credentials before restoring normal operations.
