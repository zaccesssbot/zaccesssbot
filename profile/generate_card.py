#!/usr/bin/env python3
"""Generates the zaccesssbot profile card as two SVGs (dark and light) from live GitHub data.

Modelled on zaccesss/zaccesss's own card: the same dot-filled rows, the same paired rows and the
same Git Stats grouping, read through the same GraphQL fields, so a number means the same thing on
both cards. Scoped to what this account is, an automation account, so the identity rows say what
it runs on. The left column carries the robot avatar as ASCII art, scaled to fill the column whose
height the stats set.
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape as esc

USER = "zaccesssbot"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
GRAPHQL_URL = "https://api.github.com/graphql"

SVG_WIDTH = 1120  # same canvas width as the main card
LINE_WIDTH = 70    # character budget for a full row, every value ends at this column
PAIR_LEFT = 34     # left half's budget in a dual row
PAIR_RIGHT = 33    # right half's budget; 34 + 33 + 3 (" | ") = 70, matching LINE_WIDTH exactly
STATS_X = 410      # left edge of the stats column, same as the main card
ASCII_X = 35       # left edge of the art column, same as the main card
ROW_START = 40
ROW_STEP = 20
STATS_FONT_SIZE = 16  # the main card's row size: 70 chars at 16px end 38px short of the right edge, matching the left margin
ART_FONT_SIZE = 13    # the art's natural size before scaling, the main card's portrait size
FONT = "Consolas, Menlo, monospace"
CHAR_WIDTH = ART_FONT_SIZE * 0.6   # advance width of the monospace fonts above at the art's size
ART_STEP = 13                      # the art's line height; with CHAR_WIDTH it gives near-square cells
ART_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "robot_ascii.txt")
# commit subjects whose diffs are generated output rather than code, left out of Lines of Code
GENERATED_SUBJECTS = ("chore: update metadata backup", "chore: refresh profile card")

DARK = {"bg": "#05070D", "text": "#FAFAFA", "key": "#ffa657", "value": "#5778DB", "dots": "#616e7f", "add": "#3fb950", "delete": "#f85149"}
LIGHT = {"bg": "#FAFAFA", "text": "#05070D", "key": "#953800", "value": "#2445A8", "dots": "#8b93a7", "add": "#1a7f37", "delete": "#cf222e"}

IDENTITY = [
    ("Host", "github.com/zaccesssbot"),
    ("Owner", "zaccesss (Isaac Adjei)"),
    ("Mood", "shipping, not sleeping"),
    ("Status", "rm -rf boring_tasks && automate"),
    ("Runs on", "GitHub Actions, Cloudflare Workers"),
    ("Role", "automation account for Isaac's repositories"),
]
CONTACT = [
    ("Site", "isaacadjei.me"),
    ("Main", "github.com/zaccesss"),
    ("Email", "automation@isaacadjei.me"),
]


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def graphql(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    if result.get("errors"):
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result["data"]


def get_user_info() -> dict:
    data = graphql("""
        query ($login: String!) {
            user(login: $login) {
                id
                createdAt
                followers { totalCount }
                pullRequests { totalCount }
                issues { totalCount }
                gists(first: 1, privacy: PUBLIC) { totalCount }
                repositoriesContributedTo(
                    first: 1
                    contributionTypes: [COMMIT, PULL_REQUEST, PULL_REQUEST_REVIEW, ISSUE, REPOSITORY]
                    includeUserRepositories: true
                ) { totalCount }
            }
        }""", {"login": USER})["user"]
    return {
        "id": data["id"],
        "created_at": data["createdAt"],
        "followers": data["followers"]["totalCount"],
        "prs": data["pullRequests"]["totalCount"],
        "issues": data["issues"]["totalCount"],
        "gists": data["gists"]["totalCount"],
        "contrib_repos": data["repositoriesContributedTo"]["totalCount"],
    }


def get_repos() -> tuple[int, int, int]:
    """(repos, forks, stars) across everything this account owns."""
    repos = forks = stars = 0
    cursor = None
    while True:
        data = graphql("""
            query ($login: String!, $cursor: String) {
                user(login: $login) {
                    repositories(first: 100, after: $cursor, ownerAffiliations: [OWNER]) {
                        nodes { isFork stargazerCount }
                        pageInfo { hasNextPage endCursor }
                    }
                }
            }""", {"login": USER, "cursor": cursor})["user"]["repositories"]
        for n in data["nodes"]:
            repos += 1
            forks += 1 if n["isFork"] else 0
            stars += n["stargazerCount"]
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return repos, forks, stars


def get_year(year: int) -> tuple[int, int, int, list[tuple[str, int]]]:
    """(commits, reviews, total contributions, [(date, count), ...]) for one calendar year."""
    data = graphql("""
        query ($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    totalCommitContributions
                    totalPullRequestReviewContributions
                    contributionCalendar {
                        totalContributions
                        weeks { contributionDays { date contributionCount } }
                    }
                }
            }
        }""", {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
    c = data["user"]["contributionsCollection"]
    days = [(d["date"], d["contributionCount"]) for w in c["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return c["totalCommitContributions"], c["totalPullRequestReviewContributions"], c["contributionCalendar"]["totalContributions"], days


def get_contributions(created_at: str) -> tuple[int, int, int, int, int]:
    """(commits, reviews, total, current streak, best streak) across the account's whole life.
    contributionsCollection answers one year at a time, so every year since creation is walked."""
    commits = reviews = total = 0
    days: list[tuple[str, int]] = []
    for year in range(int(created_at[:4]), dt.datetime.now(dt.timezone.utc).year + 1):
        try:
            c, r, t, d = get_year(year)
        except Exception as e:  # noqa: BLE001
            print(f"  warning (contributions {year}): {e}", file=sys.stderr)
            continue
        commits += c
        reviews += r
        total += t
        days += d
    days.sort()
    # the account's commits keep their original dates once history is credited to it, so the calendar
    # reaches back before the account existed. A streak is days of activity in a row, which cannot
    # start before the account did, so only days from its creation count towards it.
    created = created_at[:10]
    days = [(day, count) for day, count in days if day >= created]
    today = dt.date.today().isoformat()
    best = run = 0
    for day, count in days:
        if day > today:
            break
        run = run + 1 if count > 0 else 0
        best = max(best, run)
    # an empty today never breaks the streak, the day is not over yet
    past = [(d, c) for d, c in days if d <= today]
    if past and past[-1][0] == today and past[-1][1] == 0:
        past = past[:-1]
    current = 0
    for _, count in reversed(past):
        if count <= 0:
            break
        current += 1
    # the streak counts calendar days with the creation day and today both included, so an unbroken
    # run since creation is one more than the uptime's whole days. The cap holds it to the uptime figure.
    age = (dt.date.today() - dt.date.fromisoformat(created)).days
    return commits, reviews, total, min(current, age), min(best, age)


def get_loc(user_id: str) -> tuple[int, int]:
    """(additions, deletions) over every commit this account authored on the default branch of a
    repository it has committed to, forks excluded. Metadata backups and profile card refreshes are
    skipped, so JSON dumps and regenerated SVGs never count as code. In an organisation only the
    monorepo counts: the component repositories are published copies of it, credited to this
    account, so counting them would count the same code again as if the bot had written it."""
    repos = []
    cursor = None
    while True:
        data = graphql("""
            query ($login: String!, $cursor: String) {
                user(login: $login) {
                    repositoriesContributedTo(first: 100, after: $cursor, contributionTypes: [COMMIT], includeUserRepositories: true) {
                        nodes { nameWithOwner isFork defaultBranchRef { name } }
                        pageInfo { hasNextPage endCursor }
                    }
                }
            }""", {"login": USER, "cursor": cursor})["user"]["repositoriesContributedTo"]
        for n in data["nodes"]:
            if n["isFork"] or not n["defaultBranchRef"]:
                continue
            owner, name = n["nameWithOwner"].split("/", 1)
            if owner.lower() != USER.lower() and not owner.startswith("zaccesss") and name.lower() != owner.lower():
                continue  # an organisation repository other than its monorepo is a published copy
            repos.append(n["nameWithOwner"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    history_q = """
        query ($owner: String!, $name: String!, $id: ID!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                defaultBranchRef {
                    target {
                        ... on Commit {
                            history(first: 100, after: $cursor, author: { id: $id }) {
                                nodes { additions deletions messageHeadline }
                                pageInfo { hasNextPage endCursor }
                            }
                        }
                    }
                }
            }
        }"""
    add = delete = 0
    for repo in repos:
        owner, name = repo.split("/", 1)
        print(f"  loc {repo}", file=sys.stderr)
        cursor = None
        try:
            while True:
                h = graphql(history_q, {"owner": owner, "name": name, "id": user_id, "cursor": cursor})["repository"]["defaultBranchRef"]["target"]["history"]
                for c in h["nodes"]:
                    if c["messageHeadline"].startswith(GENERATED_SUBJECTS):
                        continue
                    add += c["additions"]
                    delete += c["deletions"]
                if not h["pageInfo"]["hasNextPage"]:
                    break
                cursor = h["pageInfo"]["endCursor"]
        except Exception as e:  # noqa: BLE001
            print(f"  warning (loc {repo}): {e}", file=sys.stderr)
    return add, delete


def fmt_uptime(created_at: str) -> str:
    created = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    today = dt.date.today()
    years = today.year - created.year - ((today.month, today.day) < (created.month, created.day))
    anniversary = created.replace(year=created.year + years)
    days = (today - anniversary).days
    return f"{years}y {days}d" if years else f"{days}d"


def gather_stats() -> dict:
    info = get_user_info()
    repos, forks, stars = get_repos()
    commits, reviews, total, current, best = get_contributions(info["created_at"])
    add, delete = get_loc(info["id"])
    return {
        "followers": info["followers"], "stars": stars,
        "commits": commits, "prs": info["prs"],
        "issues": info["issues"], "reviews": reviews,
        "repos": repos, "forks": forks,
        "gists": info["gists"], "contribs": total,
        "uptime": fmt_uptime(info["created_at"]), "streak": f"{current}d", "best_streak": f"{best}d",
        "loc_add": add, "loc_del": delete,
    }


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------

def cc(t):  return f'<tspan fill="{{dots}}">{esc(t)}</tspan>'
def key(t): return f'<tspan fill="{{key}}">{esc(t)}</tspan>'
def val(t): return f'<tspan fill="{{value}}">{esc(t)}</tspan>'


def text(y: int, content: str, extra: str = "") -> str:
    return f'<text x="{STATS_X}" y="{y}" font-family="{FONT}" font-size="{STATS_FONT_SIZE}"{extra} xml:space="preserve">{content}</text>'


def segment(label: str, value, width: int, leading_dot: bool) -> str:
    """One 'LABEL: DOTS VALUE' segment padded to exactly `width` chars. Only the first segment on
    a line carries the leading '. ', matching the main card."""
    n = width - len(label) - 2 - 1 - len(str(value)) - (2 if leading_dot else 0)
    dots = "." * max(1, n)
    prefix = cc(". ") if leading_dot else ""
    return prefix + key(label) + cc(f": {dots} ") + val(str(value))


def full_row(y, label, value):
    return text(y, segment(label, value, LINE_WIDTH, leading_dot=True))


def dual_row(y, l1, v1, l2, v2):
    return text(y, segment(l1, v1, PAIR_LEFT, leading_dot=True) + cc(" | ") + segment(l2, v2, PAIR_RIGHT, leading_dot=False))


def loc_row(y, additions, deletions):
    total = additions - deletions  # net change, the main card's own number
    add_str, del_str = f"{additions:,}", f"{deletions:,}"
    left = segment("Lines of Code", f"{total:,}", PAIR_LEFT, leading_dot=True)
    inner = f"{add_str}++, {del_str}--"
    pad = PAIR_RIGHT - 2 - len(inner)
    lp, rp = pad // 2, pad - pad // 2
    right = (cc("{") + cc(" " * lp) + f'<tspan fill="{{add}}">{add_str}++</tspan>' + cc(", ")
             + f'<tspan fill="{{delete}}">{del_str}--</tspan>' + cc(" " * rp) + cc("}"))
    return text(y, left + cc(" | ") + right)


def bracket_row(y, l1, v1, l2, v2, sub_label, sub_value):
    """'. L1: DOTS V1 | L2: DOTS V2 {SUB: SUBVAL}', the main card's detail row shape."""
    left = segment(l1, v1, PAIR_LEFT, leading_dot=True)
    suffix = f" {{{sub_label}: {sub_value}}}"
    # the budget also pays for the space between the dots and the value, like segment() does
    n = PAIR_RIGHT - len(f"{l2}: ") - 1 - len(str(v2)) - len(suffix)
    right = (key(l2) + cc(f": {'.' * max(1, n)} ") + val(str(v2)) + cc(" {") + key(sub_label) + cc(": ") + val(str(sub_value)) + cc("}"))
    return text(y, left + cc(" | ") + right)


def header_row(y, title):
    dashes = "-" * (LINE_WIDTH - len(title) - 1)
    return text(y, f'<tspan fill="{{text}}">{esc(title)} {esc(dashes)}</tspan>', ' font-weight="700"')


def section_row(y, title):
    dashes = "-" * (LINE_WIDTH - len(title) - 3)
    return text(y, f'<tspan fill="{{text}}">- {esc(title)} {esc(dashes)}</tspan>')


# ---------------------------------------------------------------------------
# the card
# ---------------------------------------------------------------------------

def load_art() -> list[str]:
    with open(ART_PATH, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]
    width = max(len(line) for line in lines)
    return [line.ljust(width) for line in lines]


def build_svg(mode: str, stats: dict) -> str:
    p = DARK if mode == "dark" else LIGHT
    rows = []
    y = ROW_START
    rows.append(header_row(y, f"{USER}@github"))
    y += ROW_STEP + 6
    for label, value in IDENTITY:
        rows.append(full_row(y, label, value))
        y += ROW_STEP
    y += 8
    rows.append(section_row(y, "Contact"))
    y += ROW_STEP
    for label, value in CONTACT:
        rows.append(full_row(y, label, value))
        y += ROW_STEP
    y += 8
    rows.append(section_row(y, "Git Stats"))
    y += ROW_STEP
    for l1, v1, l2, v2 in [
        ("Followers", stats["followers"], "Stars", stats["stars"]),
        ("Commits", f"{stats['commits']:,}", "PRs", stats["prs"]),
        ("Issues", stats["issues"], "Reviews", stats["reviews"]),
        ("Repos", stats["repos"], "Forks", stats["forks"]),
        ("Gists", stats["gists"], "Contribs", f"{stats['contribs']:,}"),
    ]:
        rows.append(dual_row(y, l1, v1, l2, v2))
        y += ROW_STEP
    rows.append(bracket_row(y, "Uptime", stats["uptime"], "Streak", stats["streak"], "Best", stats["best_streak"]))
    y += ROW_STEP
    rows.append(loc_row(y, stats["loc_add"], stats["loc_del"]))
    stats_bottom = y
    height = stats_bottom + ROW_STEP + 10

    # the art is scaled to the column width and sits centred on the column's height, so the two
    # halves of the card read as one block whatever the stats add up to
    art = load_art()
    column_width = STATS_X - ASCII_X - 20
    column_top, column_bottom = ROW_START - STATS_FONT_SIZE, stats_bottom
    natural_width = len(art[0]) * CHAR_WIDTH
    scale = column_width / natural_width
    art_height = len(art) * ART_STEP * scale
    top = column_top + max(0, (column_bottom - column_top - art_height) / 2)
    art_svg = "".join(
        f'<text x="0" y="{(i + 1) * ART_STEP}" font-family="{FONT}" font-size="{ART_FONT_SIZE}" fill="{{value}}" xml:space="preserve">{esc(line)}</text>'
        for i, line in enumerate(art)
    )
    art_group = f'<g transform="translate({ASCII_X},{top:.1f}) scale({scale:.4f})">{art_svg}</g>'

    body = "\n  ".join(rows) + "\n  " + art_group
    for name in ("dots", "key", "value", "text", "add", "delete"):
        body = body.replace("{" + name + "}", p[name])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{height}" viewBox="0 0 {SVG_WIDTH} {height}">\n'
            f'  <rect x="0" y="0" width="{SVG_WIDTH}" height="{height}" rx="16" fill="{p["bg"]}"/>\n'
            f'  {body}\n</svg>\n')


def main() -> None:
    if not TOKEN:
        sys.exit("GH_TOKEN is not set")
    stats = gather_stats()
    os.makedirs("profile", exist_ok=True)
    for mode in ("dark", "light"):
        with open(f"profile/profile-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(build_svg(mode, stats))
    print("stats:", stats)


if __name__ == "__main__":
    main()
