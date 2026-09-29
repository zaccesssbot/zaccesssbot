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
LINE_WIDTH = 70    # character budget for a full row; same as the main card, every value ends here
PAIR_LEFT = 34     # left half's budget in a dual row
PAIR_RIGHT = 33    # right half's budget; 34 + 33 + 3 (" | ") = 70, matching LINE_WIDTH exactly
STATS_X = 410     # same column as the main card
ASCII_X = 35      # same column as the main card
ROW_START = 40
FONT_SIZE = 13    # one size everywhere, header included, so char-width math lines up pixel for
                   # pixel and every row's right edge falls on the same column
FONT = "Consolas, Menlo, monospace"

DARK = {"bg": "#05070D", "text": "#FAFAFA", "key": "#ffa657", "value": "#5778DB", "dots": "#616e7f", "add": "#3fb950", "delete": "#f85149"}
LIGHT = {"bg": "#FAFAFA", "text": "#05070D", "key": "#953800", "value": "#2445A8", "dots": "#8b93a7", "add": "#1a7f37", "delete": "#cf222e"}

TAGLINE = [
    ("Mood", "shipping, not sleeping"),
    ("Status", "rm -rf boring_tasks && automate"),
]

ROBOT_ART_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "robot_ascii.txt")


def load_robot_art() -> list[str]:
    with open(ROBOT_ART_PATH, encoding="utf-8") as f:
        return f.read().splitlines()


ROBOT_ART = load_robot_art()

ROBOT_BASE_FONT_SIZE = 8  # base size before the fill-scale transform below
ROBOT_BASE_STEP = 8       # base line height before the fill-scale transform below


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


def compute_streak(commit_dates: list[str]) -> tuple[int, int]:
    """(current, best) consecutive-day streaks with at least one commit. Best is the longest
    run anywhere in the fetched history, not just the one ending today."""
    days = sorted({d[:10] for d in commit_dates})
    if not days:
        return 0, 0
    best = run = 1
    for i in range(1, len(days)):
        prev = datetime.fromisoformat(days[i - 1]).date()
        cur = datetime.fromisoformat(days[i]).date()
        run = run + 1 if (cur - prev).days == 1 else 1
        best = max(best, run)
    current = 0
    cursor = datetime.now(timezone.utc).date()
    day_set = set(days)
    while cursor.isoformat() in day_set:
        current += 1
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
    return current, best


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
    current_streak, best_streak = compute_streak(commit_dates)

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
        "streak": f"{current_streak}d",
        "best_streak": f"{best_streak}d",
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
    content = (segment(l1, v1, PAIR_LEFT, leading_dot=True) + cc(" | ")
               + segment(l2, v2, PAIR_RIGHT, leading_dot=False))
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">{content}</text>'


def loc_row(y, additions, deletions):
    total = additions - deletions  # net change, matching the main card's own number exactly
    label = "Lines of Code"
    lead = f"{total:,}"
    add_str, del_str = f"{additions:,}", f"{deletions:,}"
    # left half uses the exact same PAIR_LEFT budget as every dual_row, so the " | " lands on
    # the same column as Followers | Stars, Commits | PRs and the rest, not wherever this row's
    # own value length happens to push it
    left = segment(label, lead, PAIR_LEFT, leading_dot=True)
    inner = f"{add_str}++, {del_str}--"
    pad = PAIR_RIGHT - 2 - len(inner)  # 2 = the braces
    lp, rp = pad // 2, pad - pad // 2
    right = (cc("{") + cc(" " * lp)
             + f'<tspan fill="{{add}}">{add_str}++</tspan>' + cc(", ")
             + f'<tspan fill="{{delete}}">{del_str}--</tspan>' + cc(" " * rp) + cc("}"))
    content = left + cc(" | ") + right
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" xml:space="preserve">{content}</text>'


def bracket_row(y, l1, v1, l2, v2, sub_label, sub_value, left_width, right_width):
    """'. LABEL1: DOTS V1 | LABEL2: DOTS V2 {SUB: SUBVAL}', main's own dual_row_detail shape,
    measured against plain text so the closing brace lands on left_width+right_width+3 exactly."""
    left = segment(l1, v1, left_width, leading_dot=True)
    prefix2 = f"{l2}: "
    suffix2 = f" {{{sub_label}: {sub_value}}}"
    n2 = right_width - len(prefix2) - len(str(v2)) - len(suffix2)
    dots2 = "." * max(1, n2)
    right = (key(l2) + cc(f": {dots2} ") + val(str(v2)) + cc(" {")
             + key(sub_label) + cc(": ") + val(str(sub_value)) + cc("}"))
    content = left + cc(" | ") + right
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
    rows.append(section_row(y, "Git Stats"))
    y += 20
    for l1, v1, l2, v2 in [
        ("Followers", stats["followers"], "Stars", stats["stars"]),
        ("Commits", stats["commits"], "PRs", stats["prs"]),
        ("Issues", stats["issues"], "Reviews", stats["reviews"]),
        ("Repos", stats["repos"], "Forks", stats["forks"]),
        ("Gists", stats["gists"], "Contribs", stats["contribs"]),
    ]:
        rows.append(dual_row(y, l1, v1, l2, v2))
        y += 20
    rows.append(bracket_row(y, "Uptime", stats["uptime"], "Streak", stats["streak"],
                             "Best", stats["best_streak"], PAIR_LEFT, PAIR_RIGHT))
    y += 20
    rows.append(loc_row(y, stats["loc_add"], stats["loc_del"]))
    y += 20

    stats_bottom = y
    h = stats_bottom + 20
    w = SVG_WIDTH

    # this is dense pixel-mapped art (converted from the real logo), not fragile line art, so
    # it can be safely stretched with a transform to fill the column exactly on both axes,
    # rather than only centred at a fixed size
    column_width = STATS_X - ASCII_X - 20
    available_height = stats_bottom - ROW_START
    natural_width = len(ROBOT_ART[0]) * ROBOT_BASE_FONT_SIZE * 0.6
    natural_height = (len(ROBOT_ART) - 1) * ROBOT_BASE_STEP
    scale_x = column_width / natural_width
    scale_y = available_height / natural_height
    rows_svg = "".join(
        f'<text x="0" y="{i * ROBOT_BASE_STEP}" font-family="{FONT}" font-size="{ROBOT_BASE_FONT_SIZE}" '
        f'fill="{{value}}" xml:space="preserve">{esc(line)}</text>'
        for i, line in enumerate(ROBOT_ART)
    )
    robot = (f'<g transform="translate({ASCII_X},{ROW_START}) scale({scale_x:.4f},{scale_y:.4f})">'
              f'{rows_svg}</g>')

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
