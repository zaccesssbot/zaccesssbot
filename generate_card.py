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

TYPING_LINES = [
    "automating the boring bits...",
    "runs on cron, not caffeine...",
    "on behalf of @zaccesss...",
    "beep boop, shipping commits...",
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
        "age_days": age_days,
    }


def robot_glyph(cx, cy, scale, accent, tile):
    """The account's own robot mark, reused at card scale."""
    t = f"translate({cx - 22 * scale},{cy - 26 * scale}) scale({scale})"
    return f"""
  <g transform="{t}">
    <line x1="22" y1="0" x2="22" y2="8" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>
    <circle cx="22" cy="-3" r="4.5" fill="{accent}"/>
    <rect x="0" y="10" width="44" height="38" rx="12" fill="{accent}"/>
    <rect x="-7" y="22" width="7" height="14" rx="3.5" fill="{accent}"/>
    <rect x="44" y="22" width="7" height="14" rx="3.5" fill="{accent}"/>
    <circle cx="13" cy="29" r="5.5" fill="{tile}"/>
    <circle cx="31" cy="29" r="5.5" fill="{tile}"/>
    <rect x="12" y="40" width="20" height="5" rx="2.5" fill="{tile}"/>
  </g>"""


def typing_rotator(x, y, colour, lines, dur_each=3):
    total = dur_each * len(lines)
    texts = []
    for i, line in enumerate(lines):
        begin = i * dur_each
        texts.append(f"""
    <text x="{x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13" fill="{colour}" opacity="0">{line}
      <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.85;1"
               dur="{total}s" begin="{begin}s" repeatCount="indefinite"/>
    </text>""")
    return "".join(texts)


def build_svg(mode: str, stats: dict) -> str:
    p = PALETTE[mode]
    w, h = 760, 220
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
  {robot_glyph(90, 100, 1.6, p['accent'], p['tile'])}
  <text x="200" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="16"
        font-weight="700" fill="{p['text']}">zaccesssbot@github</text>
  <line x1="200" y1="46" x2="620" y2="46" stroke="{p['muted']}" stroke-opacity="0.35"/>
  {info_rows}
  {typing_rotator(200, 195, p['accent'], TYPING_LINES)}
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
