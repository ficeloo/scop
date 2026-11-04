"""Generate the README diagrams as SVG files.

Each SVG holds a light and a dark palette and picks one with
@media (prefers-color-scheme: dark), so a plain <img> works everywhere.

Usage (from the repository root):
    python3 docs/diagrams/make_diagrams.py docs/diagrams
"""
import math
import sys
from html import escape

SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, 'DejaVu Sans', sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

THEMES = {
    "light": dict(card="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#59636e",
                  box="#ffffff", boxline="#8c959f", faint="#eaeef2", acc="#0969da",
                  accfill="#ddf4ff", red="#cf222e", redfill="#ffebe9", green="#1a7f37",
                  greenfill="#dafbe1", inv="#ffffff", x="#cf222e", y="#1a7f37", z="#0969da",
                  g1="#d0d7de", g2="#afb8c1", g3="#8c959f", g4="#6e7781"),
    "dark": dict(card="#161b22", border="#30363d", text="#e6edf3", muted="#9198a1",
                 box="#0d1117", boxline="#6e7681", faint="#21262d", acc="#4493f8",
                 accfill="#0c2d6b", red="#f85149", redfill="#4b1113", green="#3fb950",
                 greenfill="#0f3d1c", inv="#0d1117", x="#f85149", y="#3fb950", z="#4493f8",
                 g1="#30363d", g2="#484f58", g3="#6e7681", g4="#8b949e"),
}

COLORS = ["text", "muted", "acc", "red", "green", "x", "y", "z", "boxline", "inv"]


def css(t):
    c = THEMES[t]
    out = [
        f".card{{fill:{c['card']};stroke:{c['border']}}}",
        f".box{{fill:{c['box']};stroke:{c['boxline']};stroke-width:1.2}}",
        f".boxacc{{fill:{c['accfill']};stroke:{c['acc']};stroke-width:1.2}}",
        f".boxred{{fill:{c['redfill']};stroke:{c['red']};stroke-width:1.2}}",
        f".boxgreen{{fill:{c['greenfill']};stroke:{c['green']};stroke-width:1.2}}",
        f".lane{{fill:{c['faint']};stroke:none}}",
        f".faint{{fill:{c['faint']};stroke:none}}",
        f".g1{{fill:{c['g1']}}} .g2{{fill:{c['g2']}}} .g3{{fill:{c['g3']}}} .g4{{fill:{c['g4']}}}",
        f".fillacc{{fill:{c['accfill']}}} .fillred{{fill:{c['redfill']}}} .fillgreen{{fill:{c['greenfill']}}}",
        f"text{{font-family:{SANS};fill:{c['text']}}}",
        f".mono{{font-family:{MONO}}}",
        ".b{font-weight:600}",
    ]
    for name in COLORS:
        out.append(f".t-{name}{{fill:{c[name]}}}")
        out.append(f".s-{name}{{stroke:{c[name]}}}")
        out.append(f".m-{name}{{fill:{c[name]};stroke:none}}")
    return "\n".join(out)


def css_both():
    return css("light") + "\n@media (prefers-color-scheme: dark) {\n" + css("dark") + "\n}"


def width_of(s, size, mono=False):
    return len(s) * size * (0.61 if mono else 0.56)


class Fig:
    def __init__(self, name, w, h, title):
        self.name, self.w, self.h, self.title = name, w, h, title
        self.el = []

    # ── primitives ────────────────────────────────────────────────────────
    def raw(self, s):
        self.el.append(s)

    def text(self, x, y, s, size=13, color="text", anchor="middle", bold=False, mono=False, italic=False):
        cls = [f"t-{color}"]
        if bold:
            cls.append("b")
        if mono:
            cls.append("mono")
        style = ' font-style="italic"' if italic else ""
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
                       f'class="{" ".join(cls)}"{style} xml:space="preserve">{escape(s)}</text>')

    def lines(self, x, y, items, size=13, gap=None, **kw):
        gap = gap or size * 1.35
        for i, s in enumerate(items):
            self.text(x, y + i * gap, s, size=size, **kw)

    def rect(self, x, y, w, h, cls="box", rx=8, dash=False):
        d = ' stroke-dasharray="5 4"' if dash else ""
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="none" class="{cls}"{d}/>')

    def line(self, x1, y1, x2, y2, color="boxline", width=1.4, dash=None, arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#ar-{color})"' if arrow else ""
        self.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" fill="none" class="s-{color}" '
                       f'stroke-width="{width}"{d}{m}/>')

    def path(self, d, color="boxline", width=1.4, dash=None, arrow=False, fill=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#ar-{color})"' if arrow else ""
        cls = f"s-{color}"
        if fill:
            cls += f" {fill}"
        self.el.append(f'<path d="{d}" fill="none" class="{cls}" stroke-width="{width}" stroke-linejoin="round"{da}{m}/>')

    def poly(self, pts, cls, stroke="boxline", width=1.2, dash=None):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<polygon points="{p}" fill="none" class="{cls} s-{stroke}" '
                       f'stroke-width="{width}" stroke-linejoin="round"{d}/>')

    def polyfill(self, pts, cls, opacity=1.0):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.el.append(f'<polygon points="{p}" class="{cls}" style="opacity:{opacity}"/>')

    def circle(self, x, y, r, cls="m-text"):
        self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="{cls}"/>')

    def arrow(self, x1, y1, x2, y2, color="boxline", label=None, side="right", size=12, dash=None,
              width=1.4, mono=False, lcolor="muted"):
        self.line(x1, y1, x2, y2, color=color, width=width, dash=dash, arrow=True)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if side == "right":
                self.text(mx + 10, my + 4, label, size=size, color=lcolor, anchor="start", mono=mono)
            elif side == "left":
                self.text(mx - 10, my + 4, label, size=size, color=lcolor, anchor="end", mono=mono)
            else:
                self.text(mx, my - 7, label, size=size, color=lcolor, mono=mono)

    # ── composites ────────────────────────────────────────────────────────
    def box(self, x, y, w, h, title, sub=(), cls="box", tsize=14, ssize=12, tmono=False, smono=False,
            tcolor="text", scolor="muted"):
        self.rect(x, y, w, h, cls)
        n = len(sub)
        block = tsize + n * ssize * 1.35
        ty = y + (h - block) / 2 + tsize * 0.85
        self.text(x + w / 2, ty, title, size=tsize, bold=True, mono=tmono, color=tcolor)
        for i, s in enumerate(sub):
            self.text(x + w / 2, ty + 6 + (i + 1) * ssize * 1.32, s, size=ssize, color=scolor, mono=smono)

    def diamond(self, cx, cy, w, h, lines_, size=12.5, cls="box"):
        pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.el.append(f'<polygon points="{p}" class="{cls}"/>')
        y0 = cy - (len(lines_) - 1) * size * 0.65 + size * 0.35
        for i, s in enumerate(lines_):
            self.text(cx, y0 + i * size * 1.3, s, size=size, bold=(i == 0))

    def svg(self, theme=None):
        markers = "".join(
            f'<marker id="ar-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="m-{c}"/></marker>'
            for c in COLORS)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="title">\n'
                f'<title id="title">{escape(self.title)}</title>\n'
                f'<style>\n{css(theme) if theme else css_both()}\n</style>\n<defs>{markers}</defs>\n'
                f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="12" class="card"/>\n'
                + "\n".join(self.el) + "\n</svg>\n")


FIGS = []


def figure(fn):
    FIGS.append(fn)
    return fn


# ═════════════════════════════════════════════════════════════════════════════
# Flow diagrams
# ═════════════════════════════════════════════════════════════════════════════

@figure
def six_steps():
    f = Fig("six-steps", 860, 340, "Scop in 6 steps")
    bw, bh, gx = 230, 86, 45
    xs = [40 + i * (bw + gx) for i in range(3)]
    rows = [
        ("ONCE, WHEN A MODEL IS LOADED", 52, "box", [
            ("1. Read the .obj file", ["a list of points (vertices)", "and faces that join them"]),
            ("2. Cut faces into triangles", ["the graphics card only", "draws triangles"]),
            ("3. Send them to the GPU", ["stored in the memory", "of the graphics card"]),
        ]),
        ("EVERY FRAME, MANY TIMES PER SECOND", 212, "boxacc", [
            ("4. Place the object", ["move, turn, then put it", "in perspective (matrices)"]),
            ("5. Colour every pixel", ["a shade of grey, or a", "piece of the texture"]),
            ("6. Show the image", ["in the window,", "then start again"]),
        ]),
    ]
    for label, y, cls, boxes in rows:
        f.text(40, y - 14, label, size=11.5, color="muted", anchor="start", bold=True)
        for i, (t, sub) in enumerate(boxes):
            f.box(xs[i], y, bw, bh, t, sub, cls=cls)
            if i < 2:
                f.arrow(xs[i] + bw + 4, y + bh / 2, xs[i + 1] - 4, y + bh / 2)
    x3, y3 = xs[2] + bw / 2, 52 + bh
    x4 = xs[0] + bw / 2
    f.path(f"M{x3},{y3 + 4} L{x3},{y3 + 24} L{x4},{y3 + 24} L{x4},{212 - 4}", arrow=True)
    x6 = xs[2] + bw
    f.path(f"M{x6 + 4},{212 + bh / 2} L{x6 + 22},{212 + bh / 2} L{x6 + 22},{212 + bh + 22} "
           f"L{x4},{212 + bh + 22} L{x4},{212 + bh + 4}", color="acc", arrow=True)
    return f


@figure
def data_pipeline():
    f = Fig("data-pipeline", 860, 560, "From the .obj file to the GPU")
    bx, bw, bh = 40, 250, 58
    nx = 320
    rows = [
        (".obj file", ["plain text"], None,
         ["v 0 0 0    v 1 0 0    v 1 1 0    v 0 1 0", "f 1 2 3 4"], True),
        ("parse_obj", ["src/obj.rs"], "reads every line",
         ["v, vt, vn  →  positions, tex_coords, normals", "f  →  one face = a list of corners (FaceVertex)"], False),
        ("triangulate_face", ["src/obj.rs"], "called on each f line",
         ["a face with n corners  →  n − 2 triangles", "f 1 2 3 4  →  (4, 1, 2) (2, 3, 4)"], True),
        ("load_model", ["src/model.rs"], "builds the vertex list",
         ["centre on the bounding box, scale to 1.5, (x, y, z) → (z, x, y)",
          "same FaceVertex = same vertex: 6 corners → 4 vertices + 6 indices"], False),
        ("staging buffer → GPU", ["src/vulkan/buffer.rs"], "copied once",
         ["vertex buffer: 4 × Vertex (pos, color, tex_coord)", "index buffer:  6 × u32 = 0 1 2  2 3 0"], True),
        ("cmd_draw_indexed", ["src/app/render.rs"], "every frame",
         ["the GPU reads the 6 indices", "→ draws 2 triangles"], False),
    ]
    y = 28
    for i, (t, sub, tag, notes, mono_notes) in enumerate(rows):
        cls = "boxacc" if i == 5 else "box"
        f.box(bx, y, bw, bh, t, sub, cls=cls, tmono=(i > 0), smono=True, ssize=11.5)
        if tag:
            f.text(nx, y + 16, tag.upper(), size=10.5, color="acc" if i == 5 else "muted", anchor="start", bold=True)
        f.lines(nx, y + (35 if tag else 24), notes, size=12 if mono_notes else 12.5, anchor="start",
                mono=mono_notes, color="text", gap=17)
        if i < len(rows) - 1:
            f.arrow(bx + bw / 2, y + bh + 2, bx + bw / 2, y + bh + 28)
        y += bh + 30
    top, bot = 28 + (bh + 30), 28 + 4 * (bh + 30) + bh
    f.line(832, top, 832, bot, color="muted", width=1.2)
    f.line(824, top, 832, top, color="muted", width=1.2)
    f.line(824, bot, 832, bot, color="muted", width=1.2)
    mid = (top + bot) / 2
    f.raw(f'<text x="846" y="{mid:.1f}" font-size="11" text-anchor="middle" class="t-muted b" '
          f'transform="rotate(90 846 {mid:.1f})">ONCE PER MODEL LOAD</text>')
    return f


@figure
def ear_clipping_loop():
    f = Fig("ear-clipping-loop", 860, 470, "triangulate_face, step by step")
    cx = 300
    f.box(cx - 150, 24, 300, 50, "face with n > 3 corners", ["one f line of the .obj"])
    f.text(cx + 170, 44, "n = 3: already a triangle,", size=12, color="muted", anchor="start")
    f.text(cx + 170, 60, "kept as it is", size=12, color="muted", anchor="start")
    f.arrow(cx, 76, cx, 100)
    f.box(cx - 170, 102, 340, 62, "project_face_2d", ["Newell normal of the face, then drop",
                                                      "the axis where it is largest → 2D points"], tmono=True)
    f.arrow(cx, 166, cx, 190)
    f.diamond(cx, 240, 410, 96, ["first corner k that is an ear?", "(prev, k, next) turns left (is_convex)",
                                 "and holds no other corner (is_in_triangle)"], size=12)
    f.arrow(cx, 288, cx, 316, label="yes", side="right", color="green", lcolor="green")
    f.box(cx - 150, 318, 300, 50, "emit triangle (prev, k, next)", ["then remove corner k"], cls="boxgreen")
    f.arrow(cx, 370, cx, 394)
    f.diamond(cx, 420, 220, 52, ["more than 3 corners left?"], size=12)
    f.path(f"M{cx - 110},420 L{cx - 232},420 L{cx - 232},240 L{cx - 207},240", color="green", arrow=True)
    f.text(cx - 238, 334, "yes", size=12, color="green", anchor="end")
    f.arrow(cx + 110, 420, cx + 250, 420, label="no", side="top")
    f.box(cx + 252, 396, 250, 50, "emit the last triangle", ["done"])
    f.arrow(cx + 205, 240, cx + 300, 240, label="no ear", side="top", color="red", lcolor="red")
    f.box(cx + 302, 210, 220, 60, "fallback: fan", ["(v0, vi, vi+1) on the", "corners that are left"], cls="boxred")
    return f


def L_px(ox, oy, s, x, y):
    return (ox + x * s, oy - y * s)


@figure
def ear_clipping_L():
    f = Fig("ear-clipping-L", 860, 410, "Fan versus ear clipping on the L face")
    s = 110
    V = {1: (2, 0), 2: (2, 1), 3: (1, 1), 4: (1, 2), 5: (0, 2), 6: (0, 0)}
    panels = [
        (60, "Fan from vertex 1 (before cb4ef8b)", [(1, 2, 3), (1, 3, 4), (1, 4, 5), (1, 5, 6)],
         [(1.8, 0.45), (1.3, 0.8), (0.75, 1.72), (0.5, 0.5)], True),
        (480, "Ear clipping (current code)", [(6, 1, 2), (6, 2, 3), (6, 3, 4), (4, 5, 6)],
         None, False),
    ]
    shades = ["g1", "g2", "g3", "g4"]
    for ox, title, tris, badges, fan in panels:
        bx, by = ox + 40, 320
        P = {k: L_px(bx, by, s, *v) for k, v in V.items()}
        f.text(ox + 150, 34, title, size=14, bold=True)
        for i, t in enumerate(tris):
            f.poly([P[k] for k in t], shades[i], stroke="text", width=1.1)
        notch = [L_px(bx, by, s, 1, 1), L_px(bx, by, s, 2, 1), L_px(bx, by, s, 2, 2), L_px(bx, by, s, 1, 2)]
        f.poly(notch, "", stroke="muted", dash="4 4", width=1)
        if fan:
            sliver = [L_px(bx, by, s, 1, 1), L_px(bx, by, s, 1.5, 1), L_px(bx, by, s, 1, 2)]
            f.poly(sliver, "m-red", stroke="red", width=1.2)
        f.text(bx + 1.62 * s, by - 1.6 * s, "outside", size=11.5, color="muted")
        f.text(bx + 1.62 * s, by - 1.6 * s + 14, "the face", size=11.5, color="muted")
        f.poly([P[k] for k in (1, 2, 3, 4, 5, 6)], "", stroke="text", width=2.2)
        for i, t in enumerate(tris):
            if badges:
                cx, cy = L_px(bx, by, s, *badges[i])
            else:
                cx = sum(P[k][0] for k in t) / 3
                cy = sum(P[k][1] for k in t) / 3
            f.circle(cx, cy, 10, "m-text")
            f.text(cx, cy + 4, str(i + 1), size=12, bold=True, color="inv")
        for k, (x, y) in P.items():
            f.circle(x, y, 4, "m-text")
            dx = {1: 12, 2: 12, 3: -10, 4: 0, 5: -12, 6: -12}[k]
            dy = {1: 16, 2: -6, 3: 18, 4: -10, 5: -8, 6: 16}[k]
            f.text(x + dx, y + dy, str(k), size=13, bold=True)
        f.text(ox + 150, 362, "   ".join(f"{i + 1}: ({a},{b},{c})" for i, (a, b, c) in enumerate(tris)), size=11.5, mono=True)
        if fan:
            f.text(ox + 150, 384, "triangles 2 and 3 spill into the notch (red)", size=12.5, color="red", bold=True)
        else:
            f.text(ox + 150, 384, "every triangle stays inside the L", size=12.5, color="green", bold=True)
    return f


@figure
def matrix_chain():
    f = Fig("matrix-chain", 860, 610, "From the .obj file to a pixel")
    bx, bw, bh = 40, 240, 60
    nx = 320
    spaces = [
        ("Model space", ["the .obj, centred, size 1.5"]),
        ("World space", ["the scene, Z is up"]),
        ("Camera space", ["camera at (0, 0, 0), looking down −Z"]),
        ("Clip space", ["4D: (x, y, z, w)"]),
        ("Pixel", ["x, y in the window, depth in [0, 1]"]),
    ]
    steps = [
        ("model = T × orientation × R_auto", "push constant",
         ["places the object in the scene: automatic spin,", "manual rotations, then the move"]),
        ("view = look_at_rh(EYE, CENTER, UP)", "uniform buffer",
         ["moves the whole world so that the camera", "sits at the origin (EYE = (3, 0, 1))"]),
        ("proj = C × perspective(45°, aspect, 0.1, 10)", "uniform buffer",
         ["perspective: w = −z, so far points get closer to the", "centre; C flips Y and maps depth to [0, 1] (Vulkan)"]),
        ("done by the GPU", "fixed function",
         ["divides x, y, z by w, then maps [−1, 1]", "to the pixels of the window (viewport)"]),
    ]
    y = 24
    gap = 52
    for i, (t, sub) in enumerate(spaces):
        f.box(bx, y, bw, bh, t, sub, cls="boxacc" if i in (0, 4) else "box", ssize=11.5)
        if i < len(steps):
            m, where, notes = steps[i]
            f.arrow(bx + bw / 2, y + bh + 2, bx + bw / 2, y + bh + gap - 2, color="acc")
            f.text(nx, y + bh + 6, m, size=12.5, mono=True, anchor="start", bold=True)
            f.text(830, y + bh + 6, where, size=10.5, color="muted", anchor="end", bold=True)
            f.lines(nx, y + bh + 24, notes, size=12, color="muted", anchor="start", gap=15)
        y += bh + gap
    f.text(430, y + 8, "shader.vert:  gl_Position = proj * view * model * vec4(inPosition, 1.0)", size=12, mono=True)
    return f


@figure
def model_order():
    f = Fig("model-order", 860, 200, "Order of the model matrix")
    y = 88
    parts = [("model = ", None), ("T", "3rd: move"), (" × ", None), ("orientation", "2nd: manual rotation"),
             (" × ", None), ("R_auto", "1st: automatic spin"), (" × ", None), ("vertex", None)]
    size = 26
    total = sum(width_of(p, size, True) for p, _ in parts)
    x = (860 - total) / 2
    centres = []
    for p, note in parts:
        w = width_of(p, size, True)
        color = "acc" if note else ("muted" if p == "vertex" else "text")
        f.text(x, y, p, size=size, mono=True, anchor="start", color=color, bold=bool(note))
        if note:
            centres.append((x + w / 2, note))
        x += w
    keys = {"3rd: move": "W A S D Q E", "2nd: manual rotation": "I K U O J L", "1st: automatic spin": "around Z (= - 0)"}
    for cx, note in centres:
        f.line(cx, y + 10, cx, y + 28, color="acc")
        f.text(cx, y + 46, note, size=13, bold=True)
        f.text(cx, y + 64, keys[note], size=12, color="muted", mono=True)
    f.arrow(700, 36, 250, 36, color="muted", label="applied to the vertex from right to left", side="top", size=12.5)
    return f


@figure
def frame_sync():
    f = Fig("frame-sync", 1040, 484, "One frame of App::render")
    lanes = [("CPU", "App::render", 60), ("GPU", "graphics queue", 190), ("Presentation", "swapchain", 320)]
    for name, sub, y in lanes:
        f.rect(20, y, 1000, 104, "lane", rx=10)
        f.text(32, y + 46, name, size=14, bold=True, anchor="start")
        f.text(32, y + 64, sub, size=11.5, color="muted", anchor="start")
    cpu = [
        ("1. wait fence", "in_flight[f]"),
        ("2. acquire", "image i"),
        ("3. wait fence", "images_in_flight[i]"),
        ("4. record", "commands + ubo"),
        ("5. submit", "queue_submit"),
        ("6. present", "queue_present_khr"),
        ("7. update", "move, f + 1"),
    ]
    x = 140
    pos = []
    for t, s in cpu:
        w = max(width_of(t, 12.5), width_of(s, 10.5, True)) + 18
        f.box(x, 82, w, 56, t, [s], tsize=12.5, ssize=10.5, smono=True)
        pos.append((x, w))
        x += w + 12
    for i in range(len(pos) - 1):
        a, b = pos[i], pos[i + 1]
        f.arrow(a[0] + a[1] + 1, 110, b[0] - 1, 110, width=1.2)
    # presentation hands out an image
    ax, aw = pos[1]
    f.arrow(ax + aw / 2, 140, ax + aw / 2, 340, width=1.2)
    f.box(ax - 10, 342, 230, 56, "hands out image i", ["signals image_available[f]"], tsize=12.5, ssize=10.5,
          smono=True)
    # GPU draw
    sx, sw = pos[4]
    gx, gw = sx - 30, 250
    f.arrow(sx + sw / 2, 140, sx + sw / 2, 210, width=1.2)
    f.rect(gx, 212, gw, 64, "boxacc")
    f.text(gx + gw / 2, 234, "draws the frame", size=12.5, bold=True)
    f.text(gx + gw / 2, 251, "waits image_available[f]", size=10.5, mono=True, color="muted")
    f.text(gx + gw / 2, 266, "signals render_finished[i], in_flight[f]", size=10, mono=True, color="muted")
    # image_available: presentation -> GPU
    f.path(f"M{ax + 222},370 C{gx - 80},370 {gx - 60},244 {gx - 2},244", color="acc", dash="6 4", arrow=True)
    f.text(ax + 232, 394, "image_available[f]", size=10.5, color="acc", mono=True, anchor="start")
    # present: call goes down on the right side of the box
    px, pw = pos[5]
    cxp = px + pw - 6
    f.arrow(cxp, 140, cxp, 340, width=1.2)
    f.box(px - 20, 342, pw + 40, 56, "shows image i", ["waits render_finished[i]"], tsize=12.5, ssize=10.5,
          smono=True)
    # render_finished: GPU -> presentation
    f.path(f"M{gx + gw - 30},278 L{gx + gw - 30},340", color="acc", dash="6 4", arrow=True)
    f.text(gx + gw - 36, 316, "render_finished[i]", size=10.5, color="acc", mono=True, anchor="end")
    # in_flight fence: GPU -> CPU, two frames later
    fx = 1005
    f.path(f"M{gx + gw + 2},230 L{fx},230 L{fx},40 L{pos[0][0] + pos[0][1] / 2},40 L{pos[0][0] + pos[0][1] / 2},80",
           color="green", dash="2 3", arrow=True)
    f.text(560, 34, "in_flight[f] is signalled when the GPU is done: step 1 of the frame that reuses f waits on it",
           size=11, color="green")
    # legend
    y = 428
    f.line(40, y - 4, 70, y - 4, color="boxline", arrow=True)
    f.text(76, y, "CPU call", size=11.5, color="muted", anchor="start")
    f.line(170, y - 4, 200, y - 4, color="acc", dash="6 4", arrow=True)
    f.text(206, y, "semaphore: GPU and presentation wait for each other", size=11.5, color="muted", anchor="start")
    f.line(540, y - 4, 570, y - 4, color="green", dash="2 3", arrow=True)
    f.text(576, y, "fence: the CPU waits for the GPU", size=11.5, color="muted", anchor="start")
    f.text(40, 452, "f = frame (0, 1, 0, 1…)   i = image_index   images_in_flight[i] = fence of the last frame "
                    "that used image i", size=11, color="muted", anchor="start", mono=True)
    f.text(40, 468, "step 5 resets in_flight[f] just before queue_submit", size=11, color="muted", anchor="start",
           mono=True)
    return f


@figure
def key_input():
    f = Fig("key-input", 900, 500, "Keyboard input")
    cx = 190
    f.box(cx - 130, 22, 260, 46, "KeyboardInput event", ["physical key (KeyCode)"], tsize=13, ssize=11.5)
    f.arrow(cx, 70, cx, 92)
    f.diamond(cx, 128, 300, 68, ["move or rotate key?", "W A S D Q E  /  I K U O J L"], size=12)
    f.arrow(cx + 150, 128, 420, 128, label="yes", side="top", color="green", lcolor="green")
    f.box(422, 100, 210, 56, "pressed_keys", ["press: insert, release: remove"], tsize=13, ssize=11.5, tmono=True)
    f.arrow(cx, 162, cx, 190, label="no", side="right")
    f.diamond(cx, 220, 200, 56, ["Left Shift?"], size=12.5)
    f.arrow(cx + 100, 220, 420, 220, label="yes", side="top", color="green", lcolor="green")
    f.box(422, 196, 210, 48, "lin_vel = 2.0", ["while held, 1.0 after"], tsize=13, ssize=11.5, tmono=True)
    f.arrow(cx, 248, cx, 276, label="no", side="right")
    f.diamond(cx, 308, 240, 60, ["pressed, and", "not a repeat?"], size=12.5)
    f.arrow(cx, 338, cx, 362, label="yes", side="right", color="green", lcolor="green")
    f.box(cx - 110, 364, 220, 44, "handle_input → Signal", [], tsize=13, tmono=True)
    f.text(cx + 124, 382, "a reload only sets a flag:", size=11, color="muted", anchor="start")
    f.text(cx + 124, 396, "done at the start of render", size=11, color="muted", anchor="start")
    sig = [("Enter", "ReloadModel (file picker)"), ("← →", "ReloadTexture (skipped in grey view)"),
           ("1 2 3", "TextureAxe, then ReloadModel"), ("M", "ToggleMeshView"),
           ("= -", "UpdateAngleSpeed ∓15°/s"), ("0", "StopRotation"), ("Escape", "Exit")]
    for i, (k, s) in enumerate(sig):
        col, row = divmod(i, 4)
        f.text(40 + col * 300, 432 + row * 17, k, size=11.5, mono=True, anchor="start", bold=True)
        f.text(40 + col * 300 + 56, 432 + row * 17, s, size=11.5, anchor="start", color="muted")
    rx, ry, rw = 656, 22, 224
    items = [
        ("dir", ["sum of the held move keys"]),
        ("world_dir", ["normalize(f·dir.x + s·dir.y", "          + u·dir.z)"]),
        ("position", ["+= world_dir × lin_vel × dt"]),
        ("axis", ["normalize(sum of the held", "          rotate keys)"]),
        ("orientation", ["= orientation", "  × R(axis, 50°/s × dt)"]),
        ("curr_angle", ["+= ang_vel × dt"]),
        ("mesh_view_value", ["± 5 × dt, kept in [0, 1]"]),
    ]
    yy = ry + 52
    body = []
    for a, bs in items:
        body.append((yy, a, True))
        yy += 15
        for b in bs:
            body.append((yy, b, False))
            yy += 14
        yy += 9
    rh = yy - ry + 34
    f.rect(rx, ry, rw, rh, "boxacc")
    f.text(rx + rw / 2, ry + 26, "Every frame (render)", size=13.5, bold=True)
    for y_, s_, bold in body:
        f.text(rx + 14, y_, s_, size=11.5 if bold else 11, mono=True, anchor="start", bold=bold,
               color="text" if bold else "muted")
    f.text(rx + 14, ry + rh - 26, "f, s, u = camera_basis(", size=10, mono=True, color="muted", anchor="start")
    f.text(rx + 14, ry + rh - 13, "    CENTER − EYE, UP)", size=10, mono=True, color="muted", anchor="start")
    f.arrow(634, 128, 654, 128, color="acc")
    f.arrow(634, 220, 654, 220, color="acc")
    return f


@figure
def modules():
    f = Fig("modules", 900, 520, "Module dependencies")
    W, H = 150, 44
    nodes = {
        "main": (355, 24, "main.rs", "window, event loop"),
        "key": (110, 110, "key.rs", "keys, Signal"),
        "app": (355, 110, "app.rs", "create, destroy"),
        "render": (240, 196, "app/render.rs", "one frame"),
        "vk": (560, 196, "vulkan/", "14 modules"),
        "model": (240, 282, "model.rs", "Vertex, load_model"),
        "ppm": (560, 282, "ppm.rs", "PPM parser"),
        "obj": (240, 368, "obj.rs", "parser, ear clipping"),
    }
    ext = {
        "winit": (620, 24, "winit", "crate"),
        "rfd": (20, 24, "rfd", "crate"),
        "vulkanalia": (730, 110, "vulkanalia", "crate"),
        "spv": (730, 282, "shaders/*.spv", "include_bytes!"),
    }
    allp = {**nodes, **ext}

    def c(n, side):
        x, y, *_ = allp[n]
        return {"t": (x + W / 2, y), "b": (x + W / 2, y + H), "l": (x, y + H / 2), "r": (x + W, y + H / 2)}[side]

    edges = [("main", "b", "key", "t"), ("main", "b", "app", "t"), ("app", "b", "render", "t"),
             ("app", "r", "vk", "t"), ("render", "r", "vk", "l"), ("render", "b", "model", "t"),
             ("render", "l", "key", "b"), ("model", "b", "obj", "t"), ("vk", "b", "ppm", "t"),
             ("key", "t", "rfd", "b"), ("main", "r", "winit", "l"), ("vk", "r", "vulkanalia", "b"),
             ("vk", "r", "spv", "t")]
    for a, sa, b, sb in edges:
        (x1, y1), (x2, y2) = c(a, sa), c(b, sb)
        e = b in ext
        f.arrow(x1, y1, x2, y2, color="muted" if e else "boxline", dash="4 3" if e else None, width=1.1)
    # app -> model (load_model at start)
    f.path(f"M{355 + W - 20},{110 + H} L{355 + W - 20},{282 + H / 2} L{240 + W + 2},{282 + H / 2}", width=1.1,
           arrow=True)
    for n, (x, y, t, s) in nodes.items():
        f.box(x, y, W, H, t, [s], tsize=12.5, ssize=10.5, tmono=True, cls="boxacc" if n == "main" else "box")
    for n, (x, y, t, s) in ext.items():
        f.rect(x, y, W, H, "box", dash=True)
        f.text(x + W / 2, y + 19, t, size=12.5, mono=True, bold=True)
        f.text(x + W / 2, y + 34, s, size=10.5, color="muted")
    # shared modules
    f.rect(40, 432, 820, 30, "faint", rx=8)
    f.text(56, 452, "math.rs", size=12, mono=True, bold=True, anchor="start")
    f.text(130, 452, "vectors, matrices: used by key, app, render, model, obj and vulkan/", size=11.5, color="muted",
           anchor="start")
    f.rect(40, 468, 820, 30, "faint", rx=8)
    f.text(56, 488, "app/data.rs", size=12, mono=True, bold=True, anchor="start")
    f.text(160, 488, "AppData, every Vulkan handle: passed as &mut AppData to key, model and vulkan/", size=11.5,
           color="muted", anchor="start")
    f.text(880, 410, "arrow = \"calls\"   ·   dashed = outside src/", size=11, color="muted", anchor="end")
    return f


# ═════════════════════════════════════════════════════════════════════════════
# Math figures
# ═════════════════════════════════════════════════════════════════════════════

def iso(ox, oy, s):
    """3D → 2D: x towards the viewer (down-left), y to the right, z up."""
    def p(x, y, z):
        return (ox + (y - 0.55 * x) * s, oy - (z - 0.32 * x) * s)
    return p


@figure
def cross_product():
    f = Fig("cross-product", 860, 400, "Cross product and camera frame")
    p = iso(190, 240, 110)
    a, b = (1.1, 0.2, 0), (0.1, 1.3, 0)
    o = p(0, 0, 0)
    f.poly([p(0, 0, 0), p(*a), p(a[0] + b[0], a[1] + b[1], 0), p(*b)], "fillacc", stroke="acc", width=1)
    for v, col in ((a, "text"), (b, "text"), ((0, 0, 1.15), "acc")):
        e = p(*v)
        f.line(o[0], o[1], e[0], e[1], color=col, width=2, arrow=True)
    ea, eb, en = p(*a), p(*b), p(0, 0, 1.15)
    f.text(ea[0] - 14, ea[1] + 6, "a", size=15, bold=True, anchor="end")
    f.text(eb[0] + 12, eb[1] + 4, "b", size=15, bold=True, anchor="start")
    f.text(en[0] + 10, en[1] + 4, "a × b", size=15, bold=True, color="acc", anchor="start", mono=True)
    f.text(210, 34, "Cross product", size=14.5, bold=True)
    f.lines(40, 330, ["• a × b is perpendicular to a and to b",
                      "• its length = area of the blue parallelogram",
                      "• order matters: b × a = −(a × b)"], size=12.5, anchor="start")
    # panel B: side view x-z, y goes into the page
    f.text(650, 34, "Camera frame, side view", size=14.5, bold=True)
    ox, oy, s = 520, 250, 70
    def q(x, z):
        return (ox + x * s, oy - z * s)
    O = q(0, 0)
    f.line(O[0] - 20, O[1], q(3.9, 0)[0], O[1], color="x", width=1.4, arrow=True)
    f.text(q(3.9, 0)[0] + 8, O[1] + 4, "x", size=13, color="x", bold=True, anchor="start")
    f.line(O[0], O[1] + 20, O[0], q(0, 2.3)[1], color="z", width=1.4, arrow=True)
    f.text(O[0] - 8, q(0, 2.3)[1] + 4, "z (UP)", size=13, color="z", bold=True, anchor="end")
    f.raw(f'<circle cx="{O[0] - 30}" cy="{O[1] + 30}" r="8" fill="none" class="s-y" stroke-width="1.4"/>')
    f.line(O[0] - 35, O[1] + 25, O[0] - 25, O[1] + 35, color="y", width=1.4)
    f.line(O[0] - 25, O[1] + 25, O[0] - 35, O[1] + 35, color="y", width=1.4)
    f.text(O[0] - 44, O[1] + 34, "y (into the page)", size=11.5, color="y", anchor="end")
    E = q(3, 1)
    f.line(E[0], E[1], O[0], O[1], color="muted", width=1, dash="4 4")
    fv, uv = (-0.949, -0.316), (-0.316, 0.949)
    L = 1.1
    ef = q(3 + fv[0] * L, 1 + fv[1] * L)
    eu = q(3 + uv[0] * L, 1 + uv[1] * L)
    f.line(E[0], E[1], ef[0], ef[1], color="text", width=2.2, arrow=True)
    f.text(ef[0] - 4, ef[1] + 18, "f", size=14, bold=True, mono=True)
    f.line(E[0], E[1], eu[0], eu[1], color="green", width=2.2, arrow=True)
    f.text(eu[0] - 8, eu[1] - 4, "u", size=14, bold=True, mono=True, color="green", anchor="end")
    f.raw(f'<circle cx="{E[0]}" cy="{E[1]}" r="9" fill="none" class="s-acc" stroke-width="1.6"/>')
    f.line(E[0] - 5, E[1] - 5, E[0] + 5, E[1] + 5, color="acc", width=1.6)
    f.line(E[0] + 5, E[1] - 5, E[0] - 5, E[1] + 5, color="acc", width=1.6)
    f.text(E[0] + 14, E[1] - 10, "EYE (3, 0, 1)", size=12, mono=True, anchor="start")
    f.text(E[0] + 14, E[1] + 22, "s: into the page", size=11.5, color="acc", anchor="start")
    f.circle(O[0], O[1], 4, "m-text")
    f.text(O[0] + 8, O[1] + 18, "CENTER (0, 0, 0)", size=12, mono=True, anchor="start")
    f.lines(460, 330, ["f = forward = normalize(CENTER − EYE)",
                       "s = right   = normalize(f × UP)  = +y here",
                       "u = up      = s × f   (already unit length)"], size=12, anchor="start", mono=True)
    return f


@figure
def perspective():
    f = Fig("perspective", 860, 440, "Perspective projection, side view")
    ex, ey = 50, 215
    half = math.radians(22.5)
    far_x = 470
    top = ey - math.tan(half) * (far_x - ex)
    bot = ey + math.tan(half) * (far_x - ex)
    f.poly([(ex, ey), (far_x, top), (far_x, bot)], "faint", stroke="boxline", width=1)
    f.line(ex, ey, 520, ey, color="muted", dash="3 4", width=1)
    f.text(526, ey + 4, "−z", size=12, color="muted", anchor="start", mono=True)
    near_x = 140
    nt, nb = ey - math.tan(half) * (near_x - ex), ey + math.tan(half) * (near_x - ex)
    f.line(near_x, nt, near_x, nb, color="acc", width=2.4)
    f.text(near_x, nb + 18, "near = 0.1", size=12, color="acc", mono=True)
    f.text(far_x, bot + 18, "far = 10", size=12, mono=True)
    f.circle(ex, ey, 5, "m-text")
    f.text(ex, ey + 22, "camera", size=12)
    r = 48
    f.path(f"M{ex + r * math.cos(half):.1f},{ey - r * math.sin(half):.1f} A{r},{r} 0 0 1 "
           f"{ex + r * math.cos(half):.1f},{ey + r * math.sin(half):.1f}", color="text", width=1.2)
    f.text(ex + 54, ey + 16, "45°", size=11.5, anchor="start", mono=True)
    for x, lab in ((250, "near object"), (420, "far object")):
        h = 64
        f.line(x, ey, x, ey - h, color="text", width=4)
        f.circle(x, ey - h, 4, "m-text")
        t = (near_x - ex) / (x - ex)
        f.line(ex, ey, x, ey - h, color="red", width=1, dash="4 3")
        f.circle(near_x, ey - h * t, 4.5, "m-red")
        f.text(x, ey + 18, lab, size=12, color="muted")
    fx = 590
    f.lines(fx, 50, ["Two objects of the same height:", "the far one hits the near plane",
                     "closer to the centre (red dots),", "so it looks smaller."], size=13, bold=True, anchor="start",
            gap=18)
    f.text(fx, 150, "After P and the division by w:", size=12.5, anchor="start", bold=True)
    f.lines(fx, 176, ["fovy = 45° (vertical)", "w  = −z", "x' = (f / aspect) · x / −z", "y' = f · y / −z", "f  = cot(fovy / 2)", "",
                      "z' = −1 at near, 1 at far", "(before C maps it to [0, 1])"], size=12, anchor="start",
            mono=True, gap=19)
    f.text(40, 425, "not to scale: near (0.1) is drawn much further from the camera", size=11, color="muted",
           italic=True, anchor="start")
    return f


@figure
def vulkan_correction():
    f = Fig("vulkan-correction", 860, 340, "Vulkan correction matrix")

    def square(ox, oy, title, yup, zrange):
        s = 150
        f.text(ox + s / 2, 36, title, size=14, bold=True)
        f.rect(ox, oy, s, s, "box", rx=2)
        cx, cy = ox + s / 2, oy + s / 2
        f.line(ox - 10, cy, ox + s + 14, cy, color="x", width=1.4, arrow=True)
        f.text(ox + s + 22, cy + 4, "x", size=13, color="x", bold=True)
        if yup:
            f.line(cx, oy + s + 10, cx, oy - 14, color="y", width=1.4, arrow=True)
            f.text(cx + 10, oy - 8, "+y", size=13, color="y", bold=True, anchor="start")
            top, bottom = "y = +1", "y = −1"
        else:
            f.line(cx, oy - 10, cx, oy + s + 14, color="y", width=1.4, arrow=True)
            f.text(cx + 10, oy + s + 16, "+y", size=13, color="y", bold=True, anchor="start")
            top, bottom = "y = −1", "y = +1"
        f.text(ox - 8, oy + 10, top, size=11, color="muted", anchor="end", mono=True)
        f.text(ox - 8, oy + s, bottom, size=11, color="muted", anchor="end", mono=True)
        # the same object, upright on screen
        ax = ox + 36
        f.line(ax, cy + 46, ax, cy - 40, color="acc", width=3)
        f.path(f"M{ax - 12},{cy - 24} L{ax},{cy - 42} L{ax + 12},{cy - 24}", color="acc", width=3)
        f.text(ox + s / 2, oy + s + 46, f"depth z: {zrange}", size=12.5, mono=True)

    square(80, 70, "After perspective (OpenGL rules)", True, "−1 … 1")
    square(600, 70, "After C × perspective (Vulkan)", False, "0 … 1")
    f.arrow(310, 145, 560, 145, color="acc", width=2)
    f.text(435, 128, "C", size=18, mono=True, bold=True, color="acc")
    f.lines(435, 176, ["row 2:  y' = −y", "row 3:  z' = z/2 + w/2", "after ÷ w:  (z + 1) / 2"], size=12, mono=True,
            gap=18)
    f.text(430, 322, "Vulkan's y axis points down and its depth goes from 0 to 1. C flips y so the image stays "
                     "upright (blue arrow).", size=11.5, color="muted")
    return f


@figure
def axis_angle():
    f = Fig("axis-angle", 860, 380, "Rotation around an axis")
    ox, oy = 230, 320
    cx, cy, rx, ry = 230, 170, 150, 42
    f.line(ox, oy + 10, ox, 60, color="acc", width=2.2, arrow=True)
    f.text(ox + 10, 66, "axis k (unit length)", size=13, color="acc", bold=True, anchor="start")

    def pt(t):
        return (cx + rx * math.cos(t), cy + ry * math.sin(t))

    pts = [pt(i * 2 * math.pi / 72) for i in range(73)]
    f.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), color="muted", width=1.2, dash="4 3")
    t0, t1 = math.radians(180), math.radians(70)
    v, v2 = pt(t0), pt(t1)
    f.line(ox, oy, v[0], v[1], color="text", width=2, arrow=True)
    f.line(ox, oy, v2[0], v2[1], color="red", width=2, arrow=True)
    f.text(v[0] - 10, v[1] + 4, "v", size=15, bold=True, anchor="end", mono=True)
    f.text(v2[0] + 10, v2[1] + 16, "R · v", size=15, bold=True, color="red", anchor="start", mono=True)
    f.line(cx, cy, v[0], v[1], color="muted", width=1, dash="3 3")
    f.line(cx, cy, v2[0], v2[1], color="muted", width=1, dash="3 3")
    arc = [(cx + rx * 0.5 * math.cos(t), cy + ry * 0.5 * math.sin(t)) for t in
           [t0 + (t1 - t0) * i / 24 for i in range(25)]]
    f.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in arc), color="red", width=1.6, arrow=True)
    f.text(cx - 30, cy + 38, "θ", size=16, color="red", bold=True)
    f.circle(cx, cy, 4, "m-acc")
    f.text(cx + 8, cy - 8, "k (k · v)", size=12, mono=True, color="acc", anchor="start")
    f.text(cx, 360, "the part of v along k does not move; the rest turns on the circle", size=12, color="muted")
    f.text(230, 34, "v turns by θ around k", size=14, bold=True)
    x = 490
    f.text(x, 80, "Vector form (Rodrigues):", size=13, bold=True, anchor="start")
    f.text(x, 106, "R·v = v cos θ + (k × v) sin θ", size=13, mono=True, anchor="start")
    f.text(x, 126, "      + k (k · v)(1 − cos θ)", size=13, mono=True, anchor="start")
    f.text(x, 168, "from_axis_angle builds the same thing", size=12.5, anchor="start")
    f.text(x, 186, "as a matrix. With k = Z, its top-left", size=12.5, anchor="start")
    f.text(x, 204, "2 × 2 block is the 2D rotation:", size=12.5, anchor="start")
    f.lines(x + 20, 234, ["| cos θ   −sin θ |", "| sin θ    cos θ |"], size=13, mono=True, anchor="start", gap=20)
    f.text(x, 300, "R_auto = from_axis_angle(Z, curr_angle)", size=11.5, mono=True, anchor="start", color="muted")
    f.text(x, 318, "orientation × from_axis_angle(axis, …)", size=11.5, mono=True, anchor="start", color="muted")
    return f


@figure
def newell():
    f = Fig("newell", 860, 380, "Newell normal and projection to 2D")
    p = iso(170, 250, 115)
    quad = [(0.0, 0.0, 0.0), (1.1, 0.1, 0.12), (1.0, 1.5, -0.06), (0.0, 1.4, 0.1)]
    n = [0.0, 0.0, 0.0]
    for i in range(4):
        c, d = quad[i], quad[(i + 1) % 4]
        n[0] += (c[1] - d[1]) * (c[2] + d[2])
        n[1] += (c[2] - d[2]) * (c[0] + d[0])
        n[2] += (c[0] - d[0]) * (c[1] + d[1])
    k = max(range(3), key=lambda i: abs(n[i]))
    assert k == 2 and n[2] > 0, n
    P = [p(*v) for v in quad]
    f.poly(P, "fillacc", stroke="acc", width=1.6)
    off = [(-14, 4), (-10, 20), (14, 16), (10, -8)]
    for i, (x, y) in enumerate(P):
        f.circle(x, y, 4, "m-text")
        f.text(x + off[i][0], y + off[i][1], f"p{i}", size=12.5, bold=True, mono=True)
    ln = math.sqrt(sum(c * c for c in n))
    cen = [sum(v[i] for v in quad) / 4 for i in range(3)]
    tip = [cen[i] + n[i] / ln * 1.1 for i in range(3)]
    c0, c1 = p(*cen), p(*tip)
    f.line(c0[0], c0[1], c1[0], c1[1], color="red", width=2.2, arrow=True)
    f.text(c1[0] + 10, c1[1] + 4, f"n = ({n[0]:.2f}, {n[1]:.2f}, {n[2]:.2f})", size=12, bold=True, color="red",
           anchor="start", mono=True)
    f.text(200, 34, "A face that is not quite flat", size=14, bold=True)
    f.lines(40, 330, ["n_x = Σ (yᵢ − yᵢ₊₁)(zᵢ + zᵢ₊₁), same idea for n_y, n_z:",
                      "it works even if the corners are not in one plane"], size=11.5, anchor="start", color="muted")
    f.arrow(420, 180, 520, 180, color="acc", width=2, label="drop z", side="top", lcolor="acc", size=13)
    f.text(470, 204, "|n_z| is the largest", size=11.5, color="muted")
    ox, oy, s = 590, 270, 120
    f.line(ox - 20, oy + 20, ox + 210, oy + 20, color="x", width=1.2, arrow=True)
    f.text(ox + 216, oy + 24, "x", size=13, color="x", bold=True, anchor="start")
    f.line(ox - 20, oy + 20, ox - 20, oy - 200, color="y", width=1.2, arrow=True)
    f.text(ox - 26, oy - 196, "y", size=13, color="y", bold=True, anchor="end")
    Q = [(ox + v[0] * s, oy - v[1] * s) for v in quad]
    f.poly(Q, "fillacc", stroke="acc", width=1.6)
    off2 = [(-12, 18), (14, 18), (16, -6), (-14, -8)]
    for i, (x, y) in enumerate(Q):
        f.circle(x, y, 4, "m-text")
        f.text(x + off2[i][0], y + off2[i][1], f"p{i}", size=12.5, bold=True, mono=True)
    mx, my = ox + 0.55 * s, oy - 0.75 * s
    f.path(f"M{mx + 26},{my + 10} A28,28 0 1 0 {mx + 20},{my + 20}", color="acc", width=1.6, arrow=True)
    f.text(mx - 2, my + 5, "CCW", size=11, color="acc", bold=True)
    f.text(700, 34, "Same corners, in 2D", size=14, bold=True)
    f.lines(470, 330, ["n_z > 0: keep (x, y) = ((k+1) % 3, (k+2) % 3) = (x, y)",
                       "n_k < 0: the two axes are swapped, so the corners still turn CCW"], size=11.5,
            anchor="start", color="muted")
    return f


@figure
def cross_2d():
    f = Fig("cross-2d", 860, 340, "Signed area in 2D")

    def tri(ox, title, pts, note, color, fill):
        f.text(ox + 120, 34, title, size=14, bold=True)
        f.poly(pts, fill, stroke=color, width=1.6)
        cxm = sum(x for x, _ in pts) / 3
        for (x, y), lab in zip(pts, "abc"):
            f.circle(x, y, 4, "m-text")
            f.text(x + (14 if x > cxm else -14), y + 5, lab, size=13, bold=True, mono=True)
        f.lines(ox + 120, 272, note, size=12, gap=17)

    a, b, c = (60, 220), (190, 220), (150, 90)
    tri(20, "Turns left at b", [a, b, c], ["cross(a, b, c) > 0", "convex corner: can be an ear"], "green", "fillgreen")
    f.path(f"M{a[0] + 40},{a[1] - 14} L{b[0] - 30},{b[1] - 14} L{b[0] - 38},{b[1] - 50}", color="green", arrow=True)
    a, b, c = (320, 110), (450, 110), (410, 230)
    tri(290, "Turns right at b", [a, b, c], ["cross(a, b, c) < 0", "reflex corner: never an ear"], "red", "fillred")
    f.path(f"M{a[0] + 40},{a[1] + 14} L{b[0] - 30},{b[1] + 14} L{b[0] - 38},{b[1] + 50}", color="red", arrow=True)
    a, b, c = (580, 230), (800, 230), (690, 80)
    tri(570, "Point in triangle", [a, b, c],
        ["cross(p, b, c) ≥ 0, cross(a, p, c) ≥ 0", "and cross(a, b, p) ≥ 0  →  p is inside"], "acc", "fillacc")
    f.circle(690, 180, 5, "m-red")
    f.text(702, 184, "p", size=13, bold=True, color="red", anchor="start", mono=True)
    f.text(430, 326, "cross(a, b, c) = (b − a) × (c − a) = twice the signed area of the triangle (y up)",
           size=12, mono=True, color="muted")
    return f


@figure
def planar_uv():
    f = Fig("planar-uv", 860, 380, "Planar projection of the texture coordinates")
    p = iso(170, 280, 95)
    X, Y, Z = 0.35, 2.0, 1.5
    C = {(i, j, k): p(i * X, j * Y, k * Z) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    front = [C[(1, 0, 0)], C[(1, 1, 0)], C[(1, 1, 1)], C[(1, 0, 1)]]
    side = [C[(0, 1, 0)], C[(1, 1, 0)], C[(1, 1, 1)], C[(0, 1, 1)]]
    top = [C[(0, 0, 1)], C[(1, 0, 1)], C[(1, 1, 1)], C[(0, 1, 1)]]
    f.poly(front, "fillacc", stroke="acc", width=1.4)
    f.poly(side, "fillred", stroke="red", width=1.4)
    f.poly(top, "fillred", stroke="red", width=1.4)
    for a in range(1, 4):
        p1, p2 = p(X, a * Y / 4, 0), p(X, a * Y / 4, Z)
        f.line(p1[0], p1[1], p2[0], p2[1], color="acc", width=0.8)
        q1, q2 = p(X, 0, a * Z / 4), p(X, Y, a * Z / 4)
        f.line(q1[0], q1[1], q2[0], q2[1], color="acc", width=0.8)
        s1, s2 = p(0, Y, a * Z / 4), p(X, Y, a * Z / 4)
        f.line(s1[0], s1[1], s2[0], s2[1], color="red", width=0.8)
        t1, t2 = p(0, a * Y / 4, Z), p(X, a * Y / 4, Z)
        f.line(t1[0], t1[1], t2[0], t2[1], color="red", width=0.8)
    ax0 = p(0.9, -0.85, 0.9)
    for v, col, lab in (((1.6, -0.85, 0.9), "x", "x"), ((0.9, -0.2, 0.9), "y", "y"), ((0.9, -0.85, 1.6), "z", "z")):
        e = p(*v)
        f.line(ax0[0], ax0[1], e[0], e[1], color=col, width=1.4, arrow=True)
        f.text(e[0] + (-10 if lab == "x" else 8), e[1] + (12 if lab == "x" else 4), lab, size=12, color=col,
               bold=True, anchor="start")
    f.text(190, 34, "Bounding box of the model", size=14, bold=True)
    f.text(40, 352, "thinnest side here: x. It is dropped; the 2 other axes become u and v.", size=12,
           color="muted", anchor="start")
    f.text(380, 160, "stretched:", size=12, color="red", anchor="start", bold=True)
    f.text(380, 176, "faces parallel to", size=12, color="red", anchor="start")
    f.text(380, 192, "the dropped axis", size=12, color="red", anchor="start")
    ox, oy, s = 610, 70, 180
    f.rect(ox, oy, s, s, "fillacc", rx=2)
    for a in range(1, 4):
        f.line(ox + a * s / 4, oy, ox + a * s / 4, oy + s, color="acc", width=0.8)
        f.line(ox, oy + a * s / 4, ox + s, oy + a * s / 4, color="acc", width=0.8)
    f.rect(ox, oy, s, s, "s-acc", rx=2)
    f.text(ox - 8, oy + 4, "(0, 0)", size=11.5, mono=True, anchor="end")
    f.text(ox + s + 8, oy + s + 4, "(1, 1)", size=11.5, mono=True, anchor="start")
    f.text(ox + s / 2, oy + s + 22, "u →", size=12.5, mono=True)
    f.text(ox - 16, oy + s / 2, "v ↓", size=12.5, mono=True, anchor="end")
    f.text(ox + s / 2, 50, "The texture (UV space)", size=14, bold=True)
    f.arrow(450, 120, 598, 120, color="acc", width=1.8)
    f.text(524, 110, "front face", size=11.5, color="acc")
    f.lines(480, 306, ["u = (p − min) / (max − min) on each axis kept",
                       "key 2 (default) keeps the 2 widest axes;",
                       "keys 1 and 3 keep the thin one (more stripes)"], size=11.5, anchor="start", color="muted")
    return f


@figure
def column_major():
    f = Fig("column-major", 860, 320, "Column-major storage of Matrix4")
    ox, oy, c = 60, 70, 56
    names = ["x", "y", "z", "w"]
    cols = ["x", "y", "z", "acc"]
    f.text(ox + 2 * c, 40, "Matrix4 { x, y, z, w }: 4 columns", size=14, bold=True)
    for j in range(4):
        f.rect(ox + j * c + 3, oy, c - 6, 4 * c, "box", rx=6)
        for i in range(4):
            f.text(ox + j * c + c / 2, oy + i * c + c / 2 + 5, f"{names[j]}.{names[i]}", size=13, mono=True,
                   color=cols[j], bold=True)
    f.text(ox + 3.5 * c, oy + 4 * c + 22, "translation", size=11.5, color="acc")
    mx, my, cw = 370, 120, 29
    f.text(mx + 8 * cw, 98, "In memory (#[repr(C)], 16 × f32): column after column", size=13, bold=True)
    for k in range(16):
        j, i = divmod(k, 4)
        f.rect(mx + k * cw, my, cw - 2, 36, "box", rx=3)
        f.text(mx + k * cw + (cw - 2) / 2, my + 15, names[j], size=11, mono=True, color=cols[j], bold=True)
        f.text(mx + k * cw + (cw - 2) / 2, my + 29, names[i], size=10.5, mono=True, color="muted")
        f.text(mx + k * cw + (cw - 2) / 2, my + 52, str(k), size=10, mono=True, color="muted")
    f.lines(mx, my + 92, ["Matrix4::new(c0r0, c0r1, c0r2, c0r3, c1r0, …) takes the values in this order.",
                          "GLSL's mat4 reads memory the same way, so the uniform buffer and the push",
                          "constant need no transpose."], size=12, anchor="start", color="muted", gap=18)
    return f


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for fn in FIGS:
        fig = fn()
        with open(f"{out}/{fig.name}.svg", "w") as fh:
            fh.write(fig.svg())
        print(fig.name)


main()
