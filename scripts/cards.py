"""
Generate the GitHub statistics cards for the profile README.

These deliberately do not use github-readme-stats, streak-stats or
github-profile-trophy. Those are single shared public instances: when their
Vercel quota runs out the whole section of the README turns into a broken image,
which is exactly what happened here in August 2026 (HTTP 402 on two of the three).

Running the query ourselves inside GitHub Actions removes that dependency
entirely. The workflow's built-in GITHUB_TOKEN is enough, so there is also no
personal access token to create, store or renew.

    GITHUB_TOKEN=... python scripts/cards.py ParshvCrafts

Writes assets/card-*-{dark,light}.svg. Standard library only.
"""

import datetime as dt
import json
import os
import sys
import urllib.request

API = "https://api.github.com/graphql"

THEMES = {
    # Card headings are neutral so the section does not read as one flat wash of
    # green. "figure" is the exception: the three streak numbers stay green,
    # because they are contribution data and green is reserved for that.
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "title": "#ffffff",
        "text": "#c9d1d9", "muted": "#8b949e", "accent": "#26a641",
        "grid": "#21262d", "figure": "#39d353",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "title": "#1f2328",
        "text": "#24292f", "muted": "#57606a", "accent": "#2ea043",
        "grid": "#eaeef2", "figure": "#216e39",
    },
}

RAMP = ["#0e4429", "#006d32", "#26a641", "#39d353"]


# --------------------------------------------------------------------------- API

def query(gql, variables, token):
    body = json.dumps({"query": gql, "variables": variables}).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Authorization": "bearer " + token,
                 "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit("GraphQL error: %s" % payload["errors"])
    return payload["data"]


PROFILE = """
query($login:String!){
  user(login:$login){
    createdAt
    followers{ totalCount }
    pullRequests(states:MERGED){ totalCount }
    issues{ totalCount }
    repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,PULL_REQUEST_REVIEW]){ totalCount }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      totalCount
      nodes{
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}){
          edges{ size node{ name color } }
        }
      }
    }
  }
}
"""

CALENDAR = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}
"""


def collect(login, token):
    user = query(PROFILE, {"login": login}, token)["user"]

    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            entry = langs.setdefault(name, {"size": 0, "color": e["node"]["color"] or "#8b949e"})
            entry["size"] += e["size"]

    # The contribution calendar only covers one year per request, so walk back
    # year by year from the account's creation date and merge the days.
    start = dt.datetime.strptime(user["createdAt"][:10], "%Y-%m-%d").date()
    today = dt.date.today()
    days, commits = {}, 0
    year = start.year
    while year <= today.year:
        lo = max(start, dt.date(year, 1, 1))
        hi = min(today, dt.date(year, 12, 31))
        data = query(CALENDAR, {
            "login": login,
            "from": lo.isoformat() + "T00:00:00Z",
            "to": hi.isoformat() + "T23:59:59Z",
        }, token)["user"]["contributionsCollection"]
        commits += data["totalCommitContributions"]
        for week in data["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        year += 1

    ordered = sorted(days.items())
    total = sum(c for _, c in ordered)

    # Today counts toward the current streak only if something landed; an empty
    # today just means the day is not over yet, so it does not break the run.
    longest = run = 0
    for _, count in ordered:
        run = run + 1 if count else 0
        longest = max(longest, run)

    current = 0
    for date, count in reversed(ordered):
        if count:
            current += 1
        elif date != today.isoformat():
            break

    return {
        "stars": stars,
        "commits": commits,
        "prs": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "repos": user["repositories"]["totalCount"],
        "contributions": total,
        "active_days": sum(1 for _, c in ordered if c),
        "current_streak": current,
        "longest_streak": longest,
        "languages": sorted(langs.items(), key=lambda kv: -kv[1]["size"]),
        "days": ordered,
    }


# ------------------------------------------------------------------------ render

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def frame(w, h, c, body, label):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img" aria-label="%s">'
        '<style>text{font-family:"Segoe UI",Ubuntu,Helvetica,Arial,sans-serif}</style>'
        '<rect x="0.5" y="0.5" width="%.1f" height="%.1f" rx="10" fill="%s" stroke="%s"/>'
        "%s</svg>"
    ) % (w, h, w, h, esc(label), w - 1, h - 1, c["bg"], c["border"], body)


def card_stats(d, c):
    # Stars, issues opened and repositories-contributed-to are deliberately
    # absent. They are real numbers and weak ones (2, 1 and 4), and a summary
    # card is not the place to lead with a weak number.
    rows = [
        ("Total contributions", d["contributions"]),
        ("Total commits", d["commits"]),
        ("Pull requests merged", d["prs"]),
        ("Repositories", d["repos"]),
        ("Languages used", len(d["languages"])),
    ]
    out = ['<text x="25" y="34" fill="%s" font-size="17" font-weight="600">GitHub statistics</text>'
           % c["title"]]
    y = 68
    for i, (label, value) in enumerate(rows):
        out.append('<text x="25" y="%d" fill="%s" font-size="13">%s</text>' % (y, c["muted"], esc(label)))
        out.append('<text x="435" y="%d" fill="%s" font-size="14" font-weight="700" '
                   'text-anchor="end">%s</text>' % (y, c["text"], f"{value:,}"))
        if i < len(rows) - 1:
            out.append('<rect x="25" y="%d" width="410" height="1" fill="%s"/>' % (y + 9, c["grid"]))
        y += 27
    return frame(460, y - 5, c, "".join(out), "GitHub statistics")


def card_streak(d, c):
    cells = [
        (str(d["current_streak"]), "Current streak", "days"),
        (str(d["longest_streak"]), "Longest streak", "days"),
        (f'{d["active_days"]:,}', "Days with a commit", "all time"),
    ]
    out = []
    for i, (big, label, sub) in enumerate(cells):
        cx = 77 + i * 153
        out.append('<text x="%d" y="60" fill="%s" font-size="34" font-weight="700" '
                   'text-anchor="middle">%s</text>' % (cx, c["figure"], esc(big)))
        out.append('<text x="%d" y="84" fill="%s" font-size="13" font-weight="600" '
                   'text-anchor="middle">%s</text>' % (cx, c["text"], esc(label)))
        out.append('<text x="%d" y="102" fill="%s" font-size="11" '
                   'text-anchor="middle">%s</text>' % (cx, c["muted"], esc(sub)))
        if i:
            out.append('<rect x="%d" y="30" width="1" height="80" fill="%s"/>' % (cx - 77, c["grid"]))
    return frame(460, 130, c, "".join(out), "Contribution streaks")


def card_langs(d, c, top=8):
    langs = d["languages"][:top]
    total = sum(v["size"] for _, v in langs) or 1
    out = ['<text x="25" y="34" fill="%s" font-size="17" font-weight="600">Most used languages</text>'
           % c["title"]]

    x = 25.0
    for name, v in langs:
        w = (v["size"] / total) * 410
        out.append('<rect x="%.2f" y="52" width="%.2f" height="11" fill="%s"/>' % (x, max(w, 1), v["color"]))
        x += w
    out.append('<rect x="25" y="52" width="410" height="11" rx="5.5" fill="none" stroke="%s"/>' % c["grid"])

    for i, (name, v) in enumerate(langs):
        col, row = i % 2, i // 2
        lx, ly = 27 + col * 210, 92 + row * 24
        pct = v["size"] / total * 100
        out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (lx + 5, ly - 4, v["color"]))
        out.append('<text x="%d" y="%d" fill="%s" font-size="12">%s</text>'
                   % (lx + 18, ly, c["text"], esc(name)))
        out.append('<text x="%d" y="%d" fill="%s" font-size="12" text-anchor="end">%.1f%%</text>'
                   % (lx + 190, ly, c["muted"], pct))
    height = 92 + ((len(langs) + 1) // 2) * 24 + 6
    return frame(460, height, c, "".join(out), "Most used languages")


def card_activity(d, c, weeks=53):
    days = d["days"][-(weeks * 7):]
    if not days:
        days = [(dt.date.today().isoformat(), 0)]

    W, H = 940, 200
    left, right, top, bottom = 40, 20, 52, 34
    pw, ph = W - left - right, H - top - bottom
    peak = max(max(v for _, v in days), 1)

    step = pw / max(len(days) - 1, 1)
    pts = [(left + i * step, top + ph - (v / peak) * ph) for i, (_, v) in enumerate(days)]
    line = " ".join("%.2f,%.2f" % p for p in pts)
    area = "%.2f,%.2f " % (left, top + ph) + line + " %.2f,%.2f" % (pts[-1][0], top + ph)

    out = ['<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0%%" stop-color="%s" stop-opacity="0.55"/>'
           '<stop offset="100%%" stop-color="%s" stop-opacity="0"/>'
           '</linearGradient></defs>' % (RAMP[2], RAMP[2]),
           '<text x="25" y="32" fill="%s" font-size="17" font-weight="600">'
           'Contribution activity</text>' % c["title"],
           '<text x="%d" y="32" fill="%s" font-size="12" text-anchor="end">'
           'past year &#183; peak %d in a day</text>' % (W - 20, c["muted"], peak)]

    for f in (0, 0.5, 1):
        y = top + ph * f
        out.append('<rect x="%d" y="%.1f" width="%d" height="1" fill="%s"/>' % (left, y, pw, c["grid"]))
        out.append('<text x="%d" y="%.1f" fill="%s" font-size="10" text-anchor="end">%d</text>'
                   % (left - 8, y + 3, c["muted"], round(peak * (1 - f))))

    out.append('<polygon points="%s" fill="url(#fade)"/>' % area)
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8" '
               'stroke-linejoin="round"/>' % (line, RAMP[3]))

    # Month ticks, drawn only where the month actually changes.
    last = None
    for i, (date, _) in enumerate(days):
        month = date[:7]
        if month != last:
            last = month
            if i:
                label = dt.date.fromisoformat(date).strftime("%b")
                out.append('<text x="%.1f" y="%d" fill="%s" font-size="10" '
                           'text-anchor="middle">%s</text>'
                           % (left + i * step, H - 12, c["muted"], label))
    return frame(W, H, c, "".join(out), "Contribution activity over the past year")


def main():
    login = sys.argv[1] if len(sys.argv) > 1 else "ParshvCrafts"
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")

    data = collect(login, token)
    os.makedirs("assets", exist_ok=True)

    builders = {"stats": card_stats, "streak": card_streak,
                "langs": card_langs, "activity": card_activity}
    for name, build in builders.items():
        for theme, colours in THEMES.items():
            path = "assets/card-%s-%s.svg" % (name, theme)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(build(data, colours))
            print("wrote", path)

    print("streak %d/%d  contributions %s  commits %s  stars %d  merged PRs %d"
          % (data["current_streak"], data["longest_streak"],
             f'{data["contributions"]:,}', f'{data["commits"]:,}',
             data["stars"], data["prs"]))


if __name__ == "__main__":
    main()
