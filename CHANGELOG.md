# Changelog

All notable changes to this repository are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Dates stand in for version numbers, since this is a living profile card rather than a released library.

---

## [Unreleased]

### Added

- `.github/workflows/README.md`, describing the workflows and the conventions they follow
- A CI workflow that compiles and imports the card generator on every pull request, so a broken change cannot land

### Changed

- The fork sync runs every six hours instead of nightly. It skips archived forks, copies each upstream's description, homepage and topics onto the fork and fails loudly when its token stops working, while one bad fork no longer stops the rest
- The Gitleaks scan can also be run by hand from the Actions tab
- The card refresh passes its signing key through an environment variable
- The card image carries descriptive alt text
- `SECURITY.md`, `CODE_OF_CONDUCT.md` and `SUPPORT.md` describe this repository and link the account's shared files

## [2026-10-02]

### Added

- A workflow that resets every fork to its upstream tip, so the forks never fall behind

### Changed

- The card follows the main card's layout: identity and Contact sections above the Git Stats, with the robot avatar as ASCII art filling the left column beside them. The numbers come from the same GraphQL fields as the main card, so commits and contributions count everything GitHub credits to the account rather than what a search index returns
- The streak counts only days since the account was created and never reads higher than the uptime, since credited history reaches back further than the account exists. Lines of Code skips card refreshes and counts only an organisation's monorepo, so regenerated SVGs and published copies never count as code
- The README no longer carries a contact line under the card

## [2026-09-29]

### Added

- Profile card generator (`generate_card.py`), pulling live stats from the GitHub API: followers, stars, commits, PRs, issues, reviews, repos, forks, gists, contribs, uptime, streak and lines of code
- Dark and light SVG cards, refreshed four times a day by a scheduled workflow
- Root files matching zaccesss/zaccesss's own structure: CODEOWNERS, `.gitattributes`, `.gitignore`, `.markdownlint.json`
