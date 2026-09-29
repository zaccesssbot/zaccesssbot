#!/usr/bin/env python3
"""Generates the zaccesssbot profile card as two SVGs (dark and light), pulling real, live
stats from the GitHub API: public repos, forks, gists, followers and account age.

Modelled on the visual system of zaccesss/zaccesss's own profile.py (the same dot-filled
neofetch row format and the same GitHub diff style colour roles: key, value, dots, text) but
scoped down to what this account actually has: no GraphQL contribution history, since a fresh
automation account has none worth showing. Unlike the main card, forks and gists are shown
here rather than hidden, since forking other projects to contribute upstream is this account's
main activity.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape as esc

USER = "zaccesssbot"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

LINE_WIDTH = 46  # character budget for the stats column; dots fill to this width exactly
STATS_X = 300
ASCII_X = 40
ROW_STEP = 20
ROW_START = 40
FONT = "Consolas, Menlo, monospace"

# same colour roles as the main card: key (label), value, dots/punctuation, text, bg
DARK = {"bg": "#05070D", "text": "#FAFAFA", "key": "#ffa657", "value": "#5778DB", "dots": "#616e7f"}
LIGHT = {"bg": "#FAFAFA", "text": "#05070D", "key": "#953800", "value": "#2445A8", "dots": "#8b93a7"}

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
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - created).days
    return {
        "repos": len(repos),
        "forks": sum(1 for r in repos if r.get("fork")),
        "gists": len(gists),
        "followers": user.get("followers", 0),
        "age": f"{age_days}d",
        "kernel": "never sleeps, doesn't need to",
    }


def pad_dots(label: str, value: str, width: int = LINE_WIDTH) -> str:
    """Return dots so '. LABEL: DOTS VALUE' = width chars exactly, same rule as the main card."""
    n = width - 2 - len(label) - 2 - 1 - len(str(value))
    return "." * max(1, n)


def cc(t):  return f'<tspan fill="{{dots}}">{esc(t)}</tspan>'
def key(t): return f'<tspan fill="{{key}}">{esc(t)}</tspan>'
def val(t): return f'<tspan fill="{{value}}">{esc(t)}</tspan>'


def info_row(y, label, value):
    content = cc(". ") + key(label) + cc(f": {pad_dots(label, str(value))} ") + val(str(value))
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="13">{content}</text>'


def robot_rows(y0):
    return "".join(
        f'<text x="{ASCII_X}" y="{y0 + i * 16}" font-family="{FONT}" font-size="11" '
        f'fill="{{value}}" xml:space="preserve">{esc(line)}</text>'
        for i, line in enumerate(ROBOT_ART)
    )


def build_svg(mode: str, stats: dict) -> str:
    p = DARK if mode == "dark" else LIGHT
    header = "zaccesssbot@github"
    dashes = "-" * (LINE_WIDTH - len(header) - 1)
    rows = [
        ("repos", stats["repos"]),
        ("forks", stats["forks"]),
        ("gists", stats["gists"]),
        ("followers", stats["followers"]),
        ("uptime", stats["age"]),
        ("kernel", stats["kernel"]),
    ]
    h = ROW_START + (len(rows) + 1) * ROW_STEP + 20
    h = max(h, ROW_START + len(ROBOT_ART) * 16 + 30)
    w = 820

    body = [f'<text x="{STATS_X}" y="{ROW_START}" font-family="{FONT}" font-size="14" '
            f'font-weight="700" fill="{p["text"]}">{esc(header)} {esc(dashes)}</text>']
    for i, (label, value) in enumerate(rows, start=1):
        body.append(info_row(ROW_START + i * ROW_STEP, label, value))
    body.append(robot_rows(ROW_START))

    svg_body = "\n  ".join(body)
    # colours are inlined per role rather than CSS classes, so the SVG behaves the same
    # whether GitHub's camo proxy strips <style> or not
    svg_body = (svg_body
                .replace("{dots}", p["dots"])
                .replace("{key}", p["key"])
                .replace("{value}", p["value"]))

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
