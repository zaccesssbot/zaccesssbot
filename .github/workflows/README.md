# Workflows

Two workflows do the account's own upkeep and three keep this repository healthy. The card generator lives in [`../../profile/generate_card.py`](../../profile/generate_card.py); its workflow only hands it a token and commits the result.

## The account's upkeep

| Workflow | Runs on | What it does |
| --- | --- | --- |
| [`update-card.yml`](update-card.yml) | Four times a day (00:00, 06:00, 12:00 and 18:00 UTC), by hand | Regenerates `profile/profile-dark.svg` and `profile/profile-light.svg` from live GitHub stats, bumps the README's cache-busting version and commits only if something changed. Commits are SSH signed with the account's registered signing key |
| [`sync-forks.yml`](sync-forks.yml) | Every six hours (00:33, 06:33, 12:33 and 18:33 UTC), by hand | Resets every fork's default branch to the upstream tip and copies the upstream's description, homepage and topics, so each fork stays an exact copy. Archived forks are left alone. A skipped or failed run costs nothing, since the next run catches up on whatever still differs |

## Repo automation

| Workflow | Runs on | What it does |
| --- | --- | --- |
| [`ci.yml`](ci.yml) | Every pull request, by hand | Compiles and imports the card generator so a broken change cannot land |
| [`gitleaks-scan.yml`](gitleaks-scan.yml) | Every push, every pull request, by hand | Scans for hard-coded secrets with a pinned Gitleaks binary |
| [`markdownlint.yml`](markdownlint.yml) | Push to `main`, every pull request, by hand | Lints every markdown file against [`.markdownlint.json`](../../.markdownlint.json) |

"By hand" means `workflow_dispatch` from the Actions tab.

## Conventions

- One workflow per job, named for what it does. Where a job has a script, the logic lives there and the workflow only hands it a token. The fork sync is small enough to live in the workflow itself.
- Every credential comes from a repository secret passed in through `env`. Nothing configurable is committed.
- Third-party actions are pinned to a full commit SHA, so a moved tag cannot change what runs.
- The card refresh pushes to `main` directly, so the branch ruleset here blocks deletion and force pushes but does not require a pull request.
