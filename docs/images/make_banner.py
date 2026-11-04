"""Generate the README banners: "SCOP" drawn as a triangle mesh.

Each letter is a polygon (straight lines and 45° corners, in the spirit of
the 42 logo), like a face of a .obj file. A few extra vertices are added at
random places on its edges, then it is cut into triangles with ear clipping,
taking the first valid ear, like triangulate_face in src/obj.rs.
Letters with a hole (O, P) are cut in two pieces first.
Each triangle gets a grey from shader.frag: clamp(mod(id, 8) / 7, 0.1, 0.95).

The SVG holds a light and a dark palette and picks one with
@media (prefers-color-scheme: dark), so a plain <img> works everywhere.

Usage (from the repository root):
    python3 docs/images/make_banner.py docs/images
It writes banner.svg in that folder.
"""
import random
import sys

W, H = 900, 200
UNIT = 18          # size of one grid unit, in pixels
LETTER_W = 6       # letter width, in units (height is 8)
GAP = 2            # space between letters, in units
SEED = 7

# Outlines in grid units (x to the right, y down). One list per piece.
LETTERS = {
    "S": [[(2, 0), (6, 0), (6, 2), (2, 2), (2, 3), (5, 3), (6, 4), (6, 6), (4, 8),
           (0, 8), (0, 6), (4, 6), (4, 5), (2, 5), (0, 3), (0, 2)]],
    "C": [[(2, 0), (6, 0), (6, 2), (2, 2), (2, 6), (6, 6), (6, 8), (2, 8), (0, 6), (0, 2)]],
    "O": [[(0, 3), (0, 2), (2, 0), (4, 0), (6, 2), (6, 5), (4, 5), (4, 2), (2, 2), (2, 3)],
          [(0, 3), (2, 3), (2, 6), (4, 6), (4, 5), (6, 5), (6, 6), (4, 8), (2, 8), (0, 6)]],
    "P": [[(0, 3), (0, 0), (4, 0), (6, 2), (6, 3.5), (4, 3.5), (4, 2), (2, 2), (2, 3)],
          [(0, 3), (2, 3), (2, 4), (4, 4), (4, 3.5), (6, 3.5), (6, 4), (4, 6), (2, 6),
           (2, 8), (0, 8)]],
}

THEMES = {
    "dark": {
        "bg": "#0d0f14", "bg_range": (16, 24), "bg_tint": 4,
        "grey": (0.28, 0.88), "edge": "#eef0f3",
    },
    "light": {
        "bg": "#f3f4f6", "bg_range": (230, 240), "bg_tint": 2,
        "grey": (0.15, 0.58), "edge": "#f7f8fa",
    },
}


def add_edge_vertices(poly, rnd):
    """Insert 0 to 2 vertices at random places on each edge longer than 1.5 units."""
    out = []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        out.append(a)
        length = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        if length < 1.5:
            continue
        count = rnd.choice((0, 1, 1, 2)) if length < 4 else rnd.choice((1, 2, 2))
        for t in sorted(rnd.uniform(0.15, 0.85) for _ in range(count)):
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def in_triangle(p, a, b, c):
    d1, d2, d3 = cross(a, b, p), cross(b, c, p), cross(c, a, p)
    neg = d1 < -1e-9 or d2 < -1e-9 or d3 < -1e-9
    pos = d1 > 1e-9 or d2 > 1e-9 or d3 > 1e-9
    return not (neg and pos)


def ear_clipping(poly):
    """Same idea as triangulate_face: always cut the first valid ear."""
    area = sum(cross((0, 0), poly[k], poly[(k + 1) % len(poly)]) for k in range(len(poly)))
    sign = 1 if area > 0 else -1
    idx = list(range(len(poly)))
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            p, c, nx = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if cross(poly[p], poly[c], poly[nx]) * sign <= 1e-9:
                continue  # not convex (or flat)
            others = (poly[o] for o in idx if o not in (p, c, nx))
            if any(in_triangle(q, poly[p], poly[c], poly[nx]) for q in others):
                continue
            tris.append((poly[p], poly[c], poly[nx]))
            idx.pop(k)
            break
        else:  # no ear: fan on what is left, like the fallback in obj.rs
            tris += [(poly[idx[0]], poly[idx[i]], poly[idx[i + 1]]) for i in range(1, len(idx) - 1)]
            return tris
    tris.append(tuple(poly[i] for i in idx))
    return tris


BG_LEVELS = 9


def background(rnd):
    """A faint jittered triangle mesh; each triangle gets one of BG_LEVELS greys."""
    step = 36
    grid = {}
    for j in range(-1, H // step + 3):
        for i in range(-1, W // step + 3):
            grid[i, j] = (i * step + rnd.uniform(-11, 11), j * step + rnd.uniform(-11, 11))
    out = []
    for j in range(-1, H // step + 2):
        for i in range(-1, W // step + 2):
            a, b, c, d = grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]
            for tri in ((a, b, c), (a, c, d)):
                out.append('<polygon points="%s" class="b%d"/>' % (pts(tri), rnd.randrange(BG_LEVELS)))
    return out


def css(theme):
    lo, hi = theme["bg_range"]
    rules = [f".bg{{fill:{theme['bg']}}}", f".bgline{{stroke:{theme['bg']}}}", f".edge{{stroke:{theme['edge']}}}"]
    for k in range(BG_LEVELS):
        rules.append(f".b{k}{{fill:{hexgrey(lo + (hi - lo) * k / (BG_LEVELS - 1), theme['bg_tint'])}}}")
    glo, ghi = theme["grey"]
    for k in range(8):
        shade = min(max(k / 7.0, 0.1), 0.95)
        rules.append(f".s{k}{{fill:{hexgrey((glo + (ghi - glo) * shade) * 255)}}}")
    return "\n".join(rules)


def hexgrey(v, tint=0):
    v = max(0, min(255, round(v)))
    return "#%02x%02x%02x" % (v, v, min(255, v + tint))


def pts(tri):
    return " ".join("%.1f,%.1f" % p for p in tri)


def build_mesh():
    """Triangles of every letter, in pixels."""
    rnd = random.Random(SEED)
    width = (len(LETTERS) * LETTER_W + (len(LETTERS) - 1) * GAP) * UNIT
    ox, oy = (W - width) / 2, (H - 8 * UNIT) / 2
    tris = []
    for li, ch in enumerate("SCOP"):
        lx = ox + li * (LETTER_W + GAP) * UNIT
        for piece in LETTERS[ch]:
            poly = [(lx + x * UNIT, oy + y * UNIT) for x, y in add_edge_vertices(piece, rnd)]
            tris += ear_clipping(poly)
    return tris


def render(tris, out_dir):
    rnd = random.Random(42)
    # The grey of each triangle depends on its index, like gl_PrimitiveID in shader.frag.
    faces = ['<polygon points="%s" class="s%d"/>' % (pts(tri), pid % 8) for pid, tri in enumerate(tris)]
    style = css(THEMES["light"]) + "\n@media (prefers-color-scheme: dark) {\n" + css(THEMES["dark"]) + "\n}"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title">
<title id="title">Scop</title>
<style>
{style}
</style>
<clipPath id="card"><rect width="{W}" height="{H}" rx="14"/></clipPath>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" class="bg"/>
<g class="bgline" stroke-width="1">
{chr(10).join(background(rnd))}
</g>
<g class="edge" stroke-width="0.9" stroke-linejoin="round" stroke-opacity="0.8">
{chr(10).join(faces)}
</g>
</g>
</svg>
'''
    with open(f"{out_dir}/banner.svg", "w") as f:
        f.write(svg)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    render(build_mesh(), out_dir)


main()
