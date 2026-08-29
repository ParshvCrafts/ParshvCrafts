"""
Build the Tech Stack icon strips as self-contained SVGs.

go-skill-icons returns a strip as an outer <svg> containing one nested <svg>
per icon. GitHub's image proxy sanitises that: nested <svg> elements are
dropped, so the rendered README showed only the first icon of each row.

This fetches each icon on its own and flattens it into a <g transform> inside a
single SVG, so the output contains only groups, paths, shapes and defs. Nothing
is nested, nothing is fetched at render time, and ids are namespaced per icon so
two icons cannot collide over a mask or gradient name.

    python scripts/techstack.py

Writes assets/stack-<group>-{dark,light}.svg. Standard library only.
"""

import os
import re
import urllib.request

SOURCE = "https://go-skill-icons.vercel.app/api/icons?i=%s&theme=%s"

CELL = 256          # icon viewBox is 256x256
SIZE = 54           # rendered icon size in px
GAP = 14            # breathing room between icons

GROUPS = [
    ("languages", ["python", "java", "typescript", "javascript", "html", "css"]),
    ("ml", ["pytorch", "tensorflow", "sklearn", "opencv", "huggingface", "langchain"]),
    ("data", ["pandas", "numpy", "spark", "postgresql", "mysql", "sqlite",
              "plotly", "seaborn", "matplotlib", "jupyter"]),
    ("tooling", ["fastapi", "flask", "react", "nextjs", "nodejs", "tailwindcss",
                 "docker", "aws", "vercel", "git", "github", "vscode"]),
]


def fetch(name, theme):
    url = SOURCE % (name, theme)
    req = urllib.request.Request(url, headers={"User-Agent": "profile-techstack"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8")


def inner_markup(doc, name):
    """Pull the icon's own markup out of the wrapper the API returns."""
    # The wrapper is <svg><g transform><svg>ICON</svg></g></svg>; take everything
    # inside the innermost <svg ...> element.
    start = doc.find("<svg", doc.find("<svg", 1) + 1) if doc.count("<svg") > 1 else -1
    if start == -1:
        raise SystemExit("unexpected shape for icon %r" % name)
    body_start = doc.index(">", start) + 1
    body_end = doc.rindex("</svg>", 0, doc.rindex("</svg>"))
    return doc[body_start:body_end]


def namespace_ids(markup, prefix):
    """Rewrite id="x" and every reference to it, so icons cannot collide."""
    ids = set(re.findall(r'id="([^"]+)"', markup))
    for i in sorted(ids, key=len, reverse=True):
        safe = "%s_%s" % (prefix, i)
        markup = markup.replace('id="%s"' % i, 'id="%s"' % safe)
        markup = markup.replace("url(#%s)" % i, "url(#%s)" % safe)
        markup = markup.replace('href="#%s"' % i, 'href="#%s"' % safe)
    return markup


def build(group, names, theme):
    scale = SIZE / float(CELL)
    parts, x = [], 0.0
    for index, name in enumerate(names):
        markup = namespace_ids(inner_markup(fetch(name, theme), name), "%s%d" % (group, index))
        parts.append('<g transform="translate(%.1f,0) scale(%.6f)"><title>%s</title>%s</g>'
                     % (x, scale, name, markup))
        x += SIZE + GAP

    width = int(len(names) * SIZE + (len(names) - 1) * GAP)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="%d" height="%d" viewBox="0 0 %d %d" fill="none" role="img" aria-label="%s">'
        "%s</svg>"
    ) % (width, SIZE, width, SIZE, ", ".join(names), "".join(parts))


def main():
    os.makedirs("assets", exist_ok=True)
    for group, names in GROUPS:
        for theme in ("dark", "light"):
            path = "assets/stack-%s-%s.svg" % (group, theme)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(build(group, names, theme))
            print("wrote %-34s %d icons  %.1f KB"
                  % (path, len(names), os.path.getsize(path) / 1024))


if __name__ == "__main__":
    main()
