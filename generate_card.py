#!/usr/bin/env python3
"""Generates the zaccesssbot profile card as two SVGs (dark and light), pulling real,
live stats from the GitHub API: public repos, forks, gists, followers and account age.
Unlike the main zaccesss/zaccesss card, forks and gists are shown here rather than hidden,
since forking other projects to contribute upstream is this account's main activity."""

import json
import os
import urllib.request
from datetime import datetime, timezone

USER = "zaccesssbot"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

PALETTE = {
    "dark": {"tile": "#05070D", "accent": "#5778DB", "text": "#FAFAFA", "muted": "#9AA5C7"},
    "light": {"tile": "#FAFAFA", "accent": "#2445A8", "text": "#05070D", "muted": "#5A6178"},
}

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
        "age_days": age_days,
    }


def robot_glyph(x, y, colour):
    """ASCII art robot, kept as plain terminal text rather than repeating the solid icon that
    is already the account's own profile picture."""
    art = [
        "    ___     ",
        "   [o o]    ",
        "  /|___|\\   ",
        " (_/   \\_)  ",
        "   |_ _|    ",
        "  _/   \\_   ",
    ]
    return "".join(
        f'<text x="{x}" y="{y + i * 18}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="14" fill="{colour}" xml:space="preserve">{line}</text>'
        for i, line in enumerate(art)
    )


def build_svg(mode: str, stats: dict) -> str:
    p = PALETTE[mode]
    w, h = 760, 190
    lines = [
        f"repos     {stats['repos']}",
        f"forks     {stats['forks']}",
        f"gists     {stats['gists']}",
        f"followers {stats['followers']}",
        f"uptime    {stats['age_days']}d",
        "kernel    never sleeps, doesn't need to",
    ]
    info_rows = "".join(
        f'<text x="200" y="{58 + i * 20}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="13" fill="{p["muted"]}">{line}</text>'
        for i, line in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect x="0" y="0" width="{w}" height="{h}" rx="16" fill="{p['tile']}"/>
  {robot_glyph(40, 70, p['accent'])}
  <text x="200" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="16"
        font-weight="700" fill="{p['text']}">zaccesssbot@github</text>
  <line x1="200" y1="46" x2="620" y2="46" stroke="{p['muted']}" stroke-opacity="0.35"/>
  {info_rows}
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
