"""
Render a photograph as a dot-matrix SVG for the profile README.

Each source pixel of a downscaled copy becomes one <circle>, quantised onto the
five-step GitHub contribution-graph palette. Brightness picks the palette step and
also drives the radius, so the portrait reads as a contribution calendar of a face.

The palette only has contrast against one background, so two files are emitted -
`<name>-dark.svg` and `<name>-light.svg` - and the README selects between them with
<picture> + prefers-color-scheme.

    python scripts/dotify.py in.jpg -o assets/portrait --cols 96 --key 60 --zoom 0.86

Only Pillow is required.
"""

import argparse
import os

from PIL import Image, ImageOps


def equalise(values):
    """Histogram-equalise a flat list of 0-255 ints. Returns floats in [0, 1]."""
    hist = [0] * 256
    for v in values:
        hist[v] += 1
    total = len(values)
    cdf, running = [0.0] * 256, 0
    for i, count in enumerate(hist):
        running += count
        cdf[i] = running / total
    return [cdf[v] for v in values]


def build(src, out_base, cols, detail, gap, square, key, zoom):
    img = Image.open(src).convert("RGB")

    if square:
        w, h = img.size
        side = int(min(w, h) * zoom)
        # Bias the crop upward: on a headshot the subject sits above centre.
        top = max(0, int((h - side) * 0.10))
        left = max(0, (w - side) // 2)
        img = img.crop((left, top, left + side, top + side))

    rows = max(1, round(cols * img.height / img.width))
    small = img.resize((cols, rows), Image.LANCZOS)

    # Sample the studio backdrop from the four corners before contrast is
    # stretched, so the key colour matches what the eye sees in the original.
    corners = [small.getpixel(p) for p in
               ((0, 0), (cols - 1, 0), (0, rows - 1), (cols - 1, rows - 1))]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    small = ImageOps.autocontrast(small, cutoff=2)
    keyed = small.resize((cols, rows))  # contrast-stretched copy used for colour
    raw = list(Image.open(src).convert("RGB").crop(
        (left, top, left + side, top + side)).resize((cols, rows), Image.LANCZOS).getdata()
    ) if square else list(small.getdata())

    drop = set()
    if key > 0:
        for i, px in enumerate(raw):
            dist = sum((px[c] - bg[c]) ** 2 for c in range(3)) ** 0.5
            if dist < key:
                drop.add(i)

    pixels = list(keyed.getdata())
    lum = [int(0.2126 * r + 0.7152 * g + 0.0722 * b) for r, g, b in pixels]
    weight = equalise(lum)

    RAMPS = {
        "dark":  ["#0d1117", "#0e4429", "#006d32", "#26a641", "#39d353"],
        # On white, "strong" has to mean darker ink rather than brighter green,
        # so the light ramp runs the opposite way through the same family.
        "light": ["#ffffff", "#40c463", "#2ea043", "#216e39", "#0b3d22"],
    }

    cell = 10.0
    r_max = cell / 2.0 - gap
    os.makedirs(os.path.dirname(out_base) or ".", exist_ok=True)

    for theme, ramp in RAMPS.items():
        circles = []
        for i in range(len(pixels)):
            if i in drop:
                continue
            # Bright source pixels become the strongest green, exactly as a busy
            # day does on the contribution calendar.
            step = min(len(ramp) - 1, int(weight[i] * len(ramp)))
            if step == 0:
                continue
            radius = r_max * ((1.0 - detail) + detail * weight[i])
            if radius < 0.35:
                continue
            cx = (i % cols) * cell + cell / 2.0
            cy = (i // cols) * cell + cell / 2.0
            circles.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s"/>'
                           % (cx, cy, radius, ramp[step]))

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'width="%d" height="%d" role="img" '
            'aria-label="Portrait rendered as a contribution-graph dot matrix">'
            "%s</svg>"
        ) % (int(cols * cell), int(rows * cell), int(cols * cell), int(rows * cell),
             "".join(circles))

        path = "%s-%s.svg" % (out_base, theme)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print("%s  %d x %d cells  %d circles  %.1f KB"
              % (path, cols, rows, len(circles), os.path.getsize(path) / 1024))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("-o", "--out", default="assets/portrait")
    p.add_argument("--cols", type=int, default=96)
    p.add_argument("--detail", type=float, default=0.55,
                   help="0 = every dot the same size, 1 = radius fully driven by luminance")
    p.add_argument("--gap", type=float, default=0.6)
    p.add_argument("--key", type=float, default=0.0,
                   help="RGB distance below which a pixel counts as backdrop and is dropped")
    p.add_argument("--zoom", type=float, default=1.0,
                   help="<1 crops tighter on the subject")
    p.add_argument("--no-square", dest="square", action="store_false")
    a = p.parse_args()
    build(a.source, a.out, a.cols, a.detail, a.gap, a.square, a.key, a.zoom)
