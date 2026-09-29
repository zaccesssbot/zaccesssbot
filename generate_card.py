#!/usr/bin/env python3
"""Generates the zaccesssbot profile card as two SVGs (dark and light), pulling real, live
stats from the GitHub API: repos, forks, gists, followers, commits, PRs, issues and account age.

Modelled on the visual system of zaccesss/zaccesss's own profile.py: the same dot-filled
neofetch row format, the same paired "label value | label value" dual rows and the same GitHub
diff style colour roles (key, value, dots, text). Scoped down to what this account actually is:
no personal fields (no host, location, IDE), and no lines-of-code add/delete stat, since a fresh
automation account with only template commits has none of that worth computing yet. Unlike the
main card, forks and gists are shown rather than hidden, since forking other projects to
contribute upstream is this account's main activity.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape as esc

USER = "zaccesssbot"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

LINE_WIDTH = 46   # character budget per half-row; dots fill to this width exactly
PAIR_WIDTH = 22   # character budget for each side of a dual row, before the " | "
STATS_X = 300
ASCII_X = 40
ROW_START = 40
FONT = "Consolas, Menlo, monospace"

DARK = {"bg": "#05070D", "text": "#FAFAFA", "key": "#ffa657", "value": "#5778DB", "dots": "#616e7f"}
LIGHT = {"bg": "#FAFAFA", "text": "#05070D", "key": "#953800", "value": "#2445A8", "dots": "#8b93a7"}

TAGLINE = [
    "mood      shipping, not sleeping",
    "status    rm -rf boring_tasks && automate",
]

ROBOT_ART = [
    "        .-------------.        ",
    "       /  .---------.  \\       ",
    "      /  /           \\  \\      ",
    "     |  |    .-----.   |  |     ",
    "     |  |   ( o   o )  |  |     ",
    "     |  |    '-----'   |  |     ",
    "      \\  \\    \\___/    /  /     ",
    "       \\  '-----------'  /      ",
    "        '---------------'       ",
    "         |     |     |          ",
    "       .-+-.   |   .-+-.        ",
    "      |     |  |  |     |       ",
    "      |     |  |  |     |       ",
    "       '---'   |   '---'        ",
    "             __|__              ",
    "            |     |             ",
    "            |     |             ",
    "            '-----'             ",
]


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def gather_stats():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100")
    gists = api(f"/users/{USER}/gists?per_page=100")
    prs = api(f"/search/issues?q=author:{USER}+type:pr")
    issues = api(f"/search/issues?q=author:{USER}+type:issue")
    commits = api(f"/search/commits?q=author:{USER}")
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - created).days
    return {
        "repos": len(repos),
        "forks": sum(1 for r in repos if r.get("fork")),
        "gists": len(gists),
        "followers": user.get("followers", 0),
        "commits": commits.get("total_count", 0),
        "prs": prs.get("total_count", 0),
        "issues": issues.get("total_count", 0),
        "uptime": f"{age_days}d",
        "kernel": "never sleeps, doesn't need to",
    }


def cc(t):  return f'<tspan fill="{{dots}}">{esc(t)}</tspan>'
def key(t): return f'<tspan fill="{{key}}">{esc(t)}</tspan>'
def val(t): return f'<tspan fill="{{value}}">{esc(t)}</tspan>'


def half(label: str, value, width: int) -> str:
    n = width - 2 - len(label) - 2 - 1 - len(str(value))
    dots = "." * max(1, n)
    return cc(". ") + key(label) + cc(f": {dots} ") + val(str(value))


def dual_row(y, l1, v1, l2, v2):
    content = half(l1, v1, PAIR_WIDTH) + cc(" | ") + half(l2, v2, PAIR_WIDTH)
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="13" xml:space="preserve">{content}</text>'


def full_row(y, label, value):
    content = half(label, value, LINE_WIDTH)
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="13" xml:space="preserve">{content}</text>'


def text_row(y, content, size=13, weight="400", colour_key="text"):
    return (f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{size}" xml:space="preserve" '
            f'font-weight="{weight}" fill="{{{colour_key}}}">{esc(content)}</text>')


def build_svg(mode: str, stats: dict) -> str:
    p = DARK if mode == "dark" else LIGHT
    header = "zaccesssbot@github"
    dashes = "-" * (LINE_WIDTH - len(header) - 1)
    stats_header = "git stats"
    stats_dashes = "-" * (LINE_WIDTH - len(stats_header) - 1)

    rows = []
    y = ROW_START
    rows.append(text_row(y, f"{header} {dashes}", size=14, weight="700"))
    y += 26
    for line in TAGLINE:
        rows.append(full_row(y, *line.split(None, 1)))
        y += 20
    y += 8
    rows.append(text_row(y, f"- {stats_header} {stats_dashes}", colour_key="text"))
    y += 20
    rows.append(dual_row(y, "repos", stats["repos"], "forks", stats["forks"]))
    y += 20
    rows.append(dual_row(y, "gists", stats["gists"], "followers", stats["followers"]))
    y += 20
    rows.append(dual_row(y, "commits", stats["commits"], "prs", stats["prs"]))
    y += 20
    rows.append(dual_row(y, "issues", stats["issues"], "uptime", stats["uptime"]))
    y += 20
    rows.append(full_row(y, "kernel", stats["kernel"]))
    y += 20

    stats_bottom = y
    h = stats_bottom + 20
    w = 820

    # scale the robot's line height so its total span matches the stats block exactly, so
    # neither column runs on past the other or leaves a dead gap
    art_span = stats_bottom - ROW_START
    art_step = art_span / (len(ROBOT_ART) - 1)
    robot = "".join(
        f'<text x="{ASCII_X}" y="{ROW_START + i * art_step:.1f}" font-family="{FONT}" font-size="11" '
        f'fill="{{value}}" xml:space="preserve">{esc(line)}</text>'
        for i, line in enumerate(ROBOT_ART)
    )

    svg_body = "\n  ".join(rows) + "\n  " + robot
    svg_body = (svg_body
                .replace("{dots}", p["dots"])
                .replace("{key}", p["key"])
                .replace("{value}", p["value"])
                .replace("{text}", p["text"]))

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
