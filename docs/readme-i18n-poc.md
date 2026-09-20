# README i18n proof of concept

This branch evaluates automated README translation without changing `main`.

## Scope

- Canonical source: `README.md` (English)
- First target: Japanese only
- Translator: `rockbenben/md-translator`, pinned to commit `25d07cebc70266ed06bcfb7e5e1ef97253c3e998`
- Execution: manual `workflow_dispatch` only
- Output: GitHub Actions artifact only; no commit, push, or pull request is created automatically

## Safety boundaries

- The workflow has `contents: read` permission only.
- No repository or provider secrets are passed to the translator.
- Relay mode is explicitly disabled.
- The PoC uses `gtxFreeAPI`; therefore the public README text is sent to that external translation endpoint. Do not use this workflow for private or sensitive documents.
- Dependency install scripts are disabled with `--ignore-scripts`.
- The translator repository is checked out at an immutable commit SHA rather than a moving tag or branch.
- Generated output must be reviewed by a human before it is committed.

## Acceptance checks

The PoC should establish whether:

1. Markdown structure remains intact.
2. Code blocks, inline code, links, and paths remain intact.
3. Project terminology such as `PDDR` is preserved.
4. The Japanese prose is useful enough for an OSS README.
5. Network/provider behavior is acceptable for public documentation.

Passing this PoC does not automatically approve rollout to other repositories or languages.
