# Repository rulesets

`protect-main.json` is the source-controlled import definition for this repository's default-branch protection.

It is derived from PDDR Kit's `protect-main` ruleset. The common protections are kept aligned with PDDR Kit, while the required status check is repository-specific.

## Local required check

This repository requires `checkpoint`, provided by the hardened PDDR Checkpoint CI.

`checkpoint` runs on every pull request. Path-filtered workflows such as tests or PDDR record validation are deliberately not required, because GitHub can otherwise wait for a required check that was never triggered.

## Applying the file

Merging this file does not change GitHub repository settings automatically. After review and merge, import it from:

`Settings -> Rules -> Rulesets -> New ruleset -> Import a ruleset`

Review the imported settings before creating the ruleset.
