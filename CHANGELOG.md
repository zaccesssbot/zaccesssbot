# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog
and this project uses date based entries rather than semantic versions, since it is a living
profile card rather than a released library.

## Unreleased

### Changed

- The card follows the main card's layout: identity and Contact sections above the Git Stats, with the robot avatar as ASCII art filling the left column beside them. The numbers come from the same GraphQL fields as the main card, so commits and contributions count everything GitHub credits to the account rather than what a search index returns
- The streak counts only days since the account was created and never reads higher than the uptime, since credited history reaches back further than the account exists. Lines of Code skips card refreshes and counts only an organisation's monorepo, so regenerated SVGs and published copies never count as code
- The README no longer carries a contact line under the card

### Added

- A nightly workflow that resets every fork to its upstream tip, so the forks never fall behind
- Profile card generator (`generate_card.py`), pulling live stats from the GitHub API: followers, stars, commits, PRs, issues, reviews, repos, forks, gists, contribs, uptime, streak and lines of code
- Dark and light SVG cards, refreshed four times a day by a scheduled workflow
- Root files matching zaccesss/zaccesss's own structure: CODEOWNERS, `.gitattributes`, `.gitignore`, `.markdownlint.json`
