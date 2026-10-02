# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog
and this project uses date based entries rather than semantic versions, since it is a living
profile card rather than a released library.

## Unreleased

### Changed

- The card follows the main card's layout: identity, Jobs and Contact sections above the Git Stats, with the robot avatar as ASCII art filling the left column beside them. The numbers come from the same GraphQL fields as the main card, so commits and contributions count everything GitHub credits to the account rather than what a search index returns

### Added

- A nightly workflow that resets every fork to its upstream tip, so the forks never fall behind
- Profile card generator (`generate_card.py`), pulling live stats from the GitHub API: followers, stars, commits, PRs, issues, reviews, repos, forks, gists, contribs, uptime, streak and lines of code
- Dark and light SVG cards, refreshed four times a day by a scheduled workflow
- Root files matching zaccesss/zaccesss's own structure: CODEOWNERS, `.gitattributes`, `.gitignore`, `.markdownlint.json`
