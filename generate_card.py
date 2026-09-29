#!/usr/bin/env python3
"""Generates the zaccesssbot profile card as two SVGs (dark and light), pulling real, live
stats from the GitHub API.

Modelled on the visual system of zaccesss/zaccesss's own profile.py: the same dot-filled
neofetch row format (one leading dot per line, every row's value ending at the same right
column regardless of label length), the same paired "label value | label value" dual rows,
the same Git Stats row grouping (Followers|Stars, Commits|PRs, Issues|Reviews, Repos|Forks,
Gists|Contribs, Uptime|Streak, Lines of Code) and the same GitHub diff style colour roles.
Scoped down to what this account actually is: no personal fields, since a fresh automation
account has none worth showing. Unlike the main card, forks and gists are shown rather than
hidden, since forking other projects to contribute upstream is this account's main activity.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape as esc

USER = "zaccesssbot"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

SVG_WIDTH = 1120  # same canvas width as zaccesss/zaccesss's own card
LINE_WIDTH = 70   # character budget for a full row; same as the main card, every value ends here
PAIR_WIDTH = 34   # character budget for each half of a dual row, before the " | "
STATS_X = 410     # same column as the main card
ASCII_X = 35      # same column as the main card
ROW_START = 40
FONT_SIZE = 13    # one size everywhere, header included, so char-width math lines up pixel for
                   # pixel and every row's right edge falls on the same column
FONT = "Consolas, Menlo, monospace"

DARK = {"bg": "#05070D", "text": "#FAFAFA", "key": "#ffa657", "value": "#5778DB", "dots": "#616e7f", "add": "#3fb950", "delete": "#f85149"}
LIGHT = {"bg": "#FAFAFA", "text": "#05070D", "key": "#953800", "value": "#2445A8", "dots": "#8b93a7", "add": "#1a7f37", "delete": "#cf222e"}

TAGLINE = [
    ("mood", "shipping, not sleeping"),
    ("status", "rm -rf boring_tasks && automate"),
]

ROBOT_ART = [
    "    ___________    ",
    "   |  .-----.  |   ",
    "   | ( o   o ) |   ",
    "   |  '-----'  |   ",
    "   |___________|   ",
    "    |    |    |    ",
    "  .-+-.  |  .-+-.  ",
    "  |   |  |  |   |  ",
    "  '---'  |  '---'  ",
    "       __|__       ",
    "      |     |      ",
    "      |_____|      ",
]
ROBOT_STEP = 16  # fixed natural line height at font-size 11, not stretched to fit the stats
                 # block, since distorting it breaks the parens' and corners' alignment


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def compute_loc(repos: list[dict]) -> tuple[int, int]:
    """Sum additions and deletions across every commit this account authored, from each
    commit's own stats. The aggregate /stats/contributors endpoint is async (returns 202 while
    GitHub computes it) and unreliable for a fresh repo, so this reads each commit directly
    instead, affordable while commit counts stay small."""
    additions = deletions = 0
    for repo in repos:
        owner_repo = repo["full_name"]
        shas = [c["sha"] for c in api(f"/repos/{owner_repo}/commits?author={USER}&per_page=100")]
        for sha in shas:
            stats = api(f"/repos/{owner_repo}/commits/{sha}").get("stats", {})
            additions += stats.get("additions", 0)
            deletions += stats.get("deletions", 0)
    return additions, deletions


def compute_streak(commit_dates: list[str]) -> int:
    """Consecutive days up to today with at least one commit, London-naive (date component only)."""
    days = {d[:10] for d in commit_dates}
    streak = 0
    cursor = datetime.now(timezone.utc).date()
    while cursor.isoformat() in days:
        streak += 1
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
    return streak


def gather_stats():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100")
    gists = api(f"/users/{USER}/gists?per_page=100")
    prs = api(f"/search/issues?q=author:{USER}+type:pr")
    issues = api(f"/search/issues?q=author:{USER}+type:issue")
    commits = api(f"/search/commits?q=author:{USER}&per_page=100")

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - created).days
    contrib_repos = {item["repository_url"] for item in prs.get("items", [])}
    commit_dates = [c["commit"]["author"]["date"] for c in commits.get("items", [])]
    additions, deletions = compute_loc(repos)

    return {
        "followers": user.get("followers", 0),
        "stars": sum(r.get("stargazers_count", 0) for r in repos),
        "commits": commits.get("total_count", 0),
        "prs": prs.get("total_count", 0),
        "issues": issues.get("total_count", 0),
        "reviews": 0,  # not available without GraphQL, and genuinely zero so far
        "repos": len(repos),
        "forks": sum(1 for r in repos if r.get("fork")),
        "gists": len(gists),
        "contribs": len(contrib_repos),
        "uptime": f"{age_days}d",
        "streak": f"{compute_streak(commit_dates)}d",
        "loc_add": additions,
        "loc_del": deletions,
    }


def cc(t):  return f'<tspan fill="{{dots}}">{esc(t)}</tspan>'
def key(t): return f'<tspan fill="{{key}}">{esc(t)}</tspan>'
def val(t): return f'<tspan fill="{{value}}">{esc(t)}</tspan>'


def segment(label: str, value, width: int, leading_dot: bool) -> str:
    """One 'LABEL: DOTS VALUE' segment, padded so it always spans exactly `width` chars.
    Only the very first segment on a line gets the leading '. ', matching the main card,
    where each full line starts with one dot, not one per label."""
    n = width - len(label) - 2 - 1 - len(str(value)) - (2 if leading_dot else 0)
    dots = "." * max(1, n)
    prefix = cc(". ") if leading_dot else ""
    return prefix + key(label) + cc(f": {dots} ") + val(str(value))


def full_row(y, label, value):
    content = segment(label, value, LINE_WIDTH, leading_dot=True)
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">{content}</text>'


def dual_row(y, l1, v1, l2, v2):
    content = (segment(l1, v1, PAIR_WIDTH, leading_dot=True) + cc(" | ")
               + segment(l2, v2, PAIR_WIDTH, leading_dot=False))
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">{content}</text>'


def loc_row(y, additions, deletions):
    total = additions - deletions  # net change, matching the main card's own number exactly
    label = "lines of code"
    lead = f"{total:,}"
    n = LINE_WIDTH - len(label) - 2 - 1 - len(lead) - 2 - len(f"{additions:,}++, {deletions:,}--")
    dots = "." * max(1, n)
    content = (cc(". ") + key(label) + cc(f": {dots} ") + val(lead) + cc(" { ")
               + f'<tspan fill="{{add}}">{additions:,}++</tspan>' + cc(", ")
               + f'<tspan fill="{{delete}}">{deletions:,}--</tspan>' + cc(" }"))
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">{content}</text>'


def header_row(y, title):
    dashes = "-" * (LINE_WIDTH - len(title) - 1)
    return (f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" '
            f'font-weight="700" fill="{{text}}" xml:space="preserve">{esc(title)} {esc(dashes)}</text>')


def section_row(y, title):
    dashes = "-" * (LINE_WIDTH - len(title) - 3)
    return (f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" '
            f'fill="{{text}}" xml:space="preserve">- {esc(title)} {esc(dashes)}</text>')


def build_svg(mode: str, stats: dict) -> str:
    p = DARK if mode == "dark" else LIGHT

    rows = []
    y = ROW_START
    rows.append(header_row(y, "zaccesssbot@github"))
    y += 26
    for label, value in TAGLINE:
        rows.append(full_row(y, label, value))
        y += 20
    y += 8
    rows.append(section_row(y, "git stats"))
    y += 20
    for l1, v1, l2, v2 in [
        ("followers", stats["followers"], "stars", stats["stars"]),
        ("commits", stats["commits"], "prs", stats["prs"]),
        ("issues", stats["issues"], "reviews", stats["reviews"]),
        ("repos", stats["repos"], "forks", stats["forks"]),
        ("gists", stats["gists"], "contribs", stats["contribs"]),
        ("uptime", stats["uptime"], "streak", stats["streak"]),
    ]:
        rows.append(dual_row(y, l1, v1, l2, v2))
        y += 20
    rows.append(loc_row(y, stats["loc_add"], stats["loc_del"]))
    y += 20

    stats_bottom = y
    h = stats_bottom + 20
    w = SVG_WIDTH

    # fixed, undistorted line height (stretching it to match the stats block breaks the
    # parens/corners alignment), vertically centred in the available space instead
    art_total = (len(ROBOT_ART) - 1) * ROBOT_STEP
    art_start = ROW_START + max(0, ((stats_bottom - ROW_START) - art_total) / 2)
    robot = "".join(
        f'<text x="{ASCII_X}" y="{art_start + i * ROBOT_STEP:.1f}" font-family="{FONT}" font-size="11" '
        f'fill="{{value}}" xml:space="preserve">{esc(line)}</text>'
        for i, line in enumerate(ROBOT_ART)
    )

    svg_body = "\n  ".join(rows) + "\n  " + robot
    svg_body = (svg_body
                .replace("{dots}", p["dots"])
                .replace("{key}", p["key"])
                .replace("{value}", p["value"])
                .replace("{text}", p["text"])
                .replace("{add}", p["add"])
                .replace("{delete}", p["delete"]))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect x="0" y="0" width="{w}" height="{h}" rx="16" fill="{p['bg']}"/>
  {svg_body}
</svg>"""


def main():
    stats = gather_stats()
    os.makedirs("profile", exist_ok=True)
    for mode in ("dark", "light"):
        with open(f"profile/profile-{mode}.svg", "w") as f:
            f.write(build_svg(mode, stats))
    print("stats:", stats)


if __name__ == "__main__":
    main()
