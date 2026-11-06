"""Builds assets/banner.svg in the style of the English Apothecary Diaries logo
(assets/source/title-en.png): same 602x310 aspect ratio and the same stacked
layout (small "The", large middle word, "Diaries" with the coffee-cup at its left).

Each piece (The / Programmer / Diaries / coffee cup) is also written on its own to
assets/components/ so it can be previewed and tuned in isolation.

Everything is vector: lettering is converted to outlines from Black Chancery
and the coffee-cup is drawn as paths, so nothing is raster and nothing is cropped
at any zoom level.

Besides the static banner (assets/banner-static.svg) it writes assets/banner.svg, a
looping "handwriting" version: every letter is written by a pen that follows the strokes a hand
would make (assets/source/pen_paths.json, computed by scripts/trace_pen_paths.py), then un-written
in reverse (pure SVG/SMIL, no scripts, so it also plays inside a GitHub <img>).

Usage: python3 scripts/build_banner.py
"""
import json
import math
import os

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = 'assets/banner.svg'
OUT_STATIC = 'assets/banner-static.svg'
COMP_DIR = 'assets/components'
LATIN_FONT = 'BLKCHCRY.TTF'
CRIMSON = '#b63952'
W, H = 602, 310
CODING_X = 11
INSET = 0.85  # shrink artwork so the glow is never clipped by the viewBox


def outline(font, text, size, x, y, tracking=0.0):
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font['head'].unitsPerEm
    pen = SVGPathPen(glyphs, ntos=lambda v: f'{v:.2f}')
    bounds = BoundsPen(glyphs)
    cursor = x
    for char in text:
        name = cmap[ord(char)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cursor, y)))
        glyphs[name].draw(TransformPen(bounds, (scale, 0, 0, -scale, cursor, y)))
        cursor += glyphs[name].width * scale + tracking
    return pen.getCommands(), bounds.bounds, cursor


def outline_chars(font, text, size, x, y, tracking=0.0):
    """Same geometry as outline(), but one entry per character: path + bounding box."""
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font['head'].unitsPerEm
    chars, cursor = [], x
    for char in text:
        name = cmap[ord(char)]
        pen = SVGPathPen(glyphs, ntos=lambda v: f'{v:.2f}')
        bounds = BoundsPen(glyphs)
        t = (scale, 0, 0, -scale, cursor, y)
        glyphs[name].draw(TransformPen(pen, t))
        glyphs[name].draw(TransformPen(bounds, t))
        chars.append({'d': pen.getCommands(), 'box': bounds.bounds})
        cursor += glyphs[name].width * scale + tracking
    return chars


# GitHub mark (Octicons "mark-github", 16x16 box): a disc with the cat cut out.
MARK_BOX = 16
MARK_SHAPE = (
    'M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 '
    '0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 '
    '0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12 '
    '-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66 '
    '-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 '
    '0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z')

# Coffee cup, drawn in a 150x120 box (x from -12 so the saucer fits).
CUP_BODY = 'M0 16 L6 82 C8 100 24 110 50 110 C76 110 92 100 94 82 L100 16 Z'
CUP_RIM = 'M0 16a50 13 0 1 0 100 0a50 13 0 1 0 -100 0Z'
CUP_COFFEE = 'M7 16a43 8.5 0 1 0 86 0a43 8.5 0 1 0 -86 0Z'
CUP_HANDLE = ('M97 30 C130 26 140 42 135 60 C130 78 112 86 89 82 L90 71 '
              'C106 73 120 67 123 57 C126 47 119 41 98 43 Z')
CUP_SAUCER = 'M-12 112a62 7 0 1 0 124 0a62 7 0 1 0 -124 0Z'
LOGO_AT, LOGO_SIZE = (50, 64), 66

FILTER = f'''<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur"/>
      <feFlood flood-color="#e24a6c" flood-opacity=".75"/>
      <feComposite in2="blur" operator="in" result="halo"/>
      <feMerge><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>'''

CUP_SCALE = 0.92
CUP_X, CUP_Y = 18 + 12 * CUP_SCALE, 309 - 120 * CUP_SCALE
CUP_TRANSFORM = f'translate({CUP_X:.1f} {CUP_Y:.1f}) scale({CUP_SCALE})'
LOGO_SCALE = LOGO_SIZE / MARK_BOX
LOGO_TRANSFORM = (f'translate({LOGO_AT[0] - LOGO_SIZE / 2} {LOGO_AT[1] - LOGO_SIZE / 2}) '
                  f'scale({LOGO_SCALE:.5f})')


def build_components():
    """Each component is its own geometry, in shared 602x310 canvas coordinates."""
    latin = TTFont(LATIN_FONT)
    return {
        'the': outline(latin, 'The', 66, 24, 51)[0],
        'programmer': outline(latin, 'Programmer', 108, CODING_X, 156, 0)[0],
        'diaries': outline(latin, 'Diaries', 138, 168, 295, 0)[0],
    }


def text_layers(names):
    """Glow (under) and white fill (over) for the given lettering components."""
    glow = ''.join(f'<use href="#{n}"/>' for n in names)
    return (
        f'<g id="glow" filter="url(#glow)">\n'
        f'      <g fill="{CRIMSON}" stroke="{CRIMSON}" stroke-width="11" stroke-linejoin="round">{glow}</g>\n'
        f'    </g>\n'
        f'    <g id="fill" fill="#fff" stroke="#fff" stroke-width="2.6" stroke-linejoin="round">{glow}</g>')


def cup_layers():
    parts = ''.join(f'<use href="#cup-{p}"/>' for p in ('body', 'rim', 'handle', 'saucer'))
    return (
        f'<g id="coffee-cup-glow" filter="url(#glow)">\n'
        f'      <g transform="{CUP_TRANSFORM}" fill="{CRIMSON}" stroke="{CRIMSON}" '
        f'stroke-width="{11 / CUP_SCALE:.1f}" stroke-linejoin="round">{parts}</g>\n'
        f'    </g>\n'
        f'    <g id="coffee-cup" transform="{CUP_TRANSFORM}">\n'
        f'      <g id="cup-shell" fill="#fff">{parts}</g>\n'
        f'      <use id="cup-coffee-surface" href="#cup-coffee" fill="{CRIMSON}"/>\n'
        f'      <use id="cup-logo" href="#github-logo-shape" transform="{LOGO_TRANSFORM}" fill="{CRIMSON}"/>\n'
        f'    </g>')


def document(parts, comps, title, inset=True):
    """parts: names among the, programmer, diaries, coffee-cup."""
    letters = [p for p in parts if p != 'coffee-cup']
    defs = ''.join(f'\n    <path id="{n}" d="{comps[n]}"/>' for n in letters)
    if 'coffee-cup' in parts:
        defs += (f'\n    <path id="cup-body" d="{CUP_BODY}"/>'
                 f'\n    <path id="cup-rim" d="{CUP_RIM}"/>'
                 f'\n    <path id="cup-coffee" d="{CUP_COFFEE}"/>'
                 f'\n    <path id="cup-handle" d="{CUP_HANDLE}"/>'
                 f'\n    <path id="cup-saucer" d="{CUP_SAUCER}"/>'
                 f'\n    <path id="github-logo-shape" d="{MARK_SHAPE}"/>')
    body = ''
    if letters:
        body += '    ' + text_layers(letters) + '\n'
    if 'coffee-cup' in parts:
        body += '    ' + cup_layers() + '\n'
    if inset:
        t = f'translate({W * (1 - INSET) / 2:.2f} {H * (1 - INSET) / 2:.2f}) scale({INSET})'
        body = f'  <g id="artwork" transform="{t}">\n{body}  </g>\n'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" role="img" aria-label="{title}">\n'
            f'  <defs>\n    {FILTER}{defs}\n  </defs>\n{body}</svg>\n')


# ---------------------------------------------------------------- animation ----
# Every letter is revealed by a pen: assets/source/pen_paths.json (made by scripts/trace_pen_paths.py)
# holds, per letter, the strokes a hand would write as points (x, y, r) -- r being the radius of the
# largest circle that fits inside the letter there -- plus a few "corner patches" for sharp corners
# the centre line cannot reach. A mask draws each stroke piece by piece with a round nib of that
# size, so the letter appears exactly where the pen has been, at the pen's own speed.
PEN_FILE = 'assets/source/pen_paths.json'
PEN_SPEED = 900      # banner units per second on a straight, open stretch of a stroke
CURVE_SLOW = 1.1     # extra slow-down in the tightest curves (1 + this at the limit)
CURVE_REF = 0.16     # curvature (radians per unit) at which that limit is reached
RAMP = 0.7           # extra slow-down when a stroke starts and when it ends...
RAMP_LEN = 9.0       # ...over this many units
LIFT = 0.05          # seconds the pen is off the paper between two strokes
LETTER_GAP = 0.06    # seconds between two letters
WORD_PAUSE = 0.14
CHUNK_LEN = 20.0     # a stroke is revealed in pieces at most this long (units)...
CHUNK_DR = 1.8       # ...and a piece never spans more than this change in stroke radius
NIB_GROW = 1.12      # nib radius = inscribed radius * NIB_GROW + NIB_PAD (never leaves a corner bare)
NIB_PAD = 2.0        # includes the 1.3-unit white outline that sits around each letter
GLOW_PAD = 7.4       # the crimson outline (5.5 units) + antialiasing: the halo runs just ahead of the pen
GLOW_CHUNK = 30.0    # the halo's nib can be coarse
PATCH_TIME = 0.06
OVERLAP = 0.08       # next cup part starts this long before the previous one ends
LEAD_IN = 0.25       # blank time at the start of every loop
HOLD = 2.0           # finished banner stays on screen before it un-writes
GAP = 0.2            # blank time after un-writing, before the next pass
MARGIN = 80          # masks reach this far past the canvas so nothing at the edges is clipped
MIRROR_AT = 0.0      # set by build_items(): time t on the way in <-> MIRROR_AT - t on the way out
EASE = '.45 .05 .55 .95'
LINEAR = '0 0 1 1'

# The cup is drawn part by part, top to bottom, like a pen sketching it:
# (id, kind, path, seconds).  'shell' = white body parts with a glowing outline,
# 'ink' = crimson details drawn on top of the white.
CUP_SEQ = [
    ('rim', 'shell', CUP_RIM, 0.45),
    ('body', 'shell', CUP_BODY, 0.75),
    ('handle', 'shell', CUP_HANDLE, 0.5),
    ('saucer', 'shell', CUP_SAUCER, 0.5),
    ('coffee', 'ink', CUP_COFFEE, 0.4),
    ('logo', 'logo', MARK_SHAPE, 0.6),
]
TRACE_W = 3.0    # px width of the white pen line while a part is being traced


def fmt(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.')


def vec(v):
    return ' '.join(fmt(x) for x in v)


def smooth(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def sample(pts, t):
    """Value (a tuple) of a [(seconds, tuple)] track at time t, eased between points, held outside."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            p = smooth((t - t0) / (t1 - t0))
            return tuple(a + (b - a) * p for a, b in zip(v0, v1))
    return pts[-1][1]


def flip(spline):
    """The easing curve of a segment played backwards (so the way out is an exact mirror)."""
    x1, y1, x2, y2 = (float(n) for n in spline.split())
    return f'{fmt(1 - x2)} {fmt(1 - y2)} {fmt(1 - x1)} {fmt(1 - y1)}'


def pingpong(pts, ease):
    """Forward points followed by the same points played backwards, plus a spline for every segment."""
    full = pts + [(MIRROR_AT - t, v) for t, v in reversed(pts)]
    forward = [ease if a[1] != b[1] else LINEAR for a, b in zip(pts, pts[1:])]
    return full, forward + [LINEAR] + [flip(sp) for sp in reversed(forward)]


def anim_track(attr, pts, total, freeze, ease=EASE, kind=None):
    """Animate one attribute (or, with kind, a transform of that type) along pts = [(seconds, tuple)]
    and then back again, looping every `total` seconds. Returns (value_string, animate_xml); the value
    is the *finished* state, so renderers without SMIL show the completed banner. freeze=t returns
    the value at that instant instead and no animation."""
    full, segs = pingpong(pts, ease)
    if freeze is not None:
        return vec(sample(full, freeze)), ''
    keys = [0.0] + [t / total for t, _ in full] + [1.0]
    vals = [full[0][1]] + [v for _, v in full] + [full[-1][1]]
    tag = 'animateTransform' if kind else 'animate'
    extra = f' type="{kind}"' if kind else ''
    xml = (f'<{tag} attributeName="{attr}"{extra} dur="{total:.2f}s" repeatCount="indefinite" '
           f'calcMode="spline" keyTimes="{";".join(fmt(k) for k in keys)}" '
           f'values="{";".join(vec(v) for v in vals)}" '
           f'keySplines="{";".join([LINEAR] + segs + [LINEAR])}"/>')
    return vec(pts[-1][1]), xml


def track(attr, pts, total, freeze, ease=EASE):
    """Scalar convenience wrapper: returns (static_attribute, animate_xml)."""
    value, xml = anim_track(attr, [(t, (v,)) for t, v in pts], total, freeze, ease)
    return f'{attr}="{value}"', xml


# ---- the pen --------------------------------------------------------------------------------
def pen_timing(stroke):
    """Seconds at which the pen reaches each point of a stroke [(x, y, r), ...].

    The pen's speed follows the shape: it slows in tight curves (the turning angle at every point
    gives the curvature) and eases in and out at the ends of the stroke."""
    p = [(x, y) for x, y, _ in stroke]
    seg = [math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]
    heading = [math.atan2(p[i + 1][1] - p[i][1], p[i + 1][0] - p[i][0]) for i in range(len(p) - 1)]
    kappa = [0.0] * len(p)
    for i in range(1, len(p) - 1):
        turn = abs((heading[i] - heading[i - 1] + math.pi) % (2 * math.pi) - math.pi)
        kappa[i] = turn / max(1e-6, (seg[i - 1] + seg[i]) / 2)
    total_len = sum(seg)
    t, run, times = 0.0, 0.0, [0.0]
    for i, ds in enumerate(seg):
        k = (kappa[i] + kappa[i + 1]) / 2
        mid = run + ds / 2
        slow = 1 + CURVE_SLOW * min(1.0, k / CURVE_REF)
        slow *= 1 + RAMP * (1 - smooth(mid / RAMP_LEN)) + RAMP * (1 - smooth((total_len - mid) / RAMP_LEN))
        t += ds * slow / PEN_SPEED
        run += ds
        times.append(t)
    return times


def make_chunks(stroke, times, t, max_len, max_dr, pad, limit_dr=True):
    """Cut a stroke into pieces, each drawn with one round nib sized for the widest part of it."""
    chunks, i = [], 0
    while i < len(stroke) - 1:
        j, length, lo, hi = i, 0.0, stroke[i][2], stroke[i][2]
        while j < len(stroke) - 1:
            nlen = length + math.dist(stroke[j][:2], stroke[j + 1][:2])
            nlo, nhi = min(lo, stroke[j + 1][2]), max(hi, stroke[j + 1][2])
            if j > i and (nlen > max_len or (limit_dr and nhi - nlo > max_dr)):
                break
            j, length, lo, hi = j + 1, nlen, nlo, nhi
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y, _ in stroke[i:j + 1])
        chunks.append({'d': d, 'w': 2 * (hi * NIB_GROW + pad), 't0': t + times[i], 't1': t + times[j]})
        i = j
    return chunks


def write_glyph(entry, t0):
    """Schedule one letter starting at t0. Returns (chunks, glow_chunks, patches, end_time)."""
    chunks, glow, patches, t, stroke_t0 = [], [], [], t0, []
    for stroke in entry['strokes']:
        if len(stroke) < 2:                      # a lone point (a dot): give it a tiny stem to draw along
            x, y, r = stroke[0]
            stroke = [[x, y, r], [x + 0.01, y, r]]
        times = pen_timing(stroke)
        stroke_t0.append((t, times))
        chunks += make_chunks(stroke, times, t, CHUNK_LEN, CHUNK_DR, NIB_PAD)
        glow += make_chunks(stroke, times, t, GLOW_CHUNK, 0, GLOW_PAD, limit_dr=False)
        t += times[-1] + LIFT
    for x, y, r, k, i in entry['patches']:
        ts, times = stroke_t0[k]
        patches.append({'x': x, 'y': y, 'r': r, 't0': ts + times[i], 't1': ts + times[i] + PATCH_TIME})
    end = max([c['t1'] for c in chunks] + [q['t1'] for q in patches])
    return chunks, glow, patches, end


def glyph_outlines():
    """Outlines of every letter of the three words, per character: {'the': [...], ...}."""
    latin = TTFont(LATIN_FONT)
    return {
        'the': outline_chars(latin, 'The', 66, 24, 51),
        'programmer': outline_chars(latin, 'Programmer', 108, CODING_X, 156, 0),
        'diaries': outline_chars(latin, 'Diaries', 138, 168, 295, 0),
    }


def build_items():
    """Writing order: The, Programmer, coffee cup (part by part), Diaries."""
    if not os.path.exists(PEN_FILE):
        raise SystemExit(f'{PEN_FILE} is missing: run  python3 scripts/trace_pen_paths.py  first')
    with open(PEN_FILE) as f:
        pen = json.load(f)
    words = glyph_outlines()
    items, cup, t = [], [], LEAD_IN
    for name in ('the', 'programmer', 'cup', 'diaries'):
        if name == 'cup':
            for pid, kind, d, dur in CUP_SEQ:
                cup.append({'id': pid, 'kind': kind, 'd': d, 'start': t, 'dur': dur})
                t += dur - OVERLAP
            t += OVERLAP + WORD_PAUSE
            continue
        for i, ch in enumerate(words[name]):
            chunks, glow, patches, end = write_glyph(pen[name][i], t)
            items.append({'id': f'{name}-{i}', 'd': ch['d'], 'chunks': chunks, 'glow_chunks': glow,
                          'patches': patches, 'start': t, 'dur': end - t})
            t = end + LETTER_GAP
        t += WORD_PAUSE - LETTER_GAP
    global MIRROR_AT
    written = max(i['start'] + i['dur'] for i in items + cup) + 0.35   # +0.35: last fills settle
    MIRROR_AT = 2 * written + HOLD
    return items, cup, MIRROR_AT + GAP


def mask_xml(it, total, freeze, glow=False):
    """A reveal mask of one letter: the nib's path, drawn piece by piece. The tight one (m-) uncovers
    the white letter exactly; the wider one (mg-) uncovers its crimson outline and glow."""
    body = []
    for c in (it['glow_chunks'] if glow else it['chunks']):
        attr, xml = track('stroke-dashoffset', [(c['t0'], 1), (c['t1'], 0)], total, freeze, LINEAR)
        body.append(f'<path d="{c["d"]}" pathLength="1" stroke-width="{c["w"]:.1f}" {attr}>{xml}</path>')
    for q in ([] if glow else it['patches']):
        attr, xml = track('r', [(q['t0'], 0), (q['t1'], q['r'])], total, freeze, LINEAR)
        body.append(f'<circle cx="{q["x"]}" cy="{q["y"]}" fill="#fff" stroke="none" {attr}>{xml}</circle>')
    return (f'<mask id="m{"g" if glow else ""}-{it["id"]}" maskUnits="userSpaceOnUse" x="{-MARGIN}" '
            f'y="{-MARGIN}" width="{W + 2 * MARGIN}" height="{H + 2 * MARGIN}">'
            f'<g fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-dasharray="1 2">{"".join(body)}</g></mask>')


def glyph_xml(it, glow):
    return f'<g mask="url(#m{"g" if glow else ""}-{it["id"]})"><use href="#g-{it["id"]}"/></g>'


def cup_xml(cup, total, freeze):
    """Glow layer + white/ink layer of the cup, each part animated on its own."""
    glow_w = 11 / CUP_SCALE
    glow, body = [], []
    for part in cup:
        t0, t1 = part['start'], part['start'] + part['dur']
        dash_attr, dash_anim = track('stroke-dashoffset', [(t0, 1), (t1, 0)], total, freeze)
        common = f'd="{part["d"]}" pathLength="1" stroke-dasharray="1 2" stroke-linejoin="round" '
        if part['kind'] == 'shell':
            # the glowing outline is traced by the pen...
            glow.append(f'<path {common}fill="none" {dash_attr}>{dash_anim}</path>')
            # ...with a thin white core line, then the white fills in and the core line fades away
            fill_attr, fill_anim = track('fill-opacity', [(t1 - 0.15, 0), (t1 + 0.25, 1)], total, freeze)
            ln_attr, ln_anim = track('stroke-opacity', [(t1 - 0.05, 1), (t1 + 0.3, 0)], total, freeze)
            body.append(f'<path {common}fill="#fff" stroke="#fff" stroke-width="{TRACE_W / CUP_SCALE:.2f}" '
                        f'{dash_attr} {fill_attr} {ln_attr}>{dash_anim}{fill_anim}{ln_anim}</path>')
        else:
            fill_attr, fill_anim = track('fill-opacity', [(t1 - 0.12, 0), (t1 + 0.2, 1)], total, freeze)
            ln_attr, ln_anim = track('stroke-opacity', [(t1 - 0.05, 1), (t1 + 0.25, 0)], total, freeze)
            width, extra = (2.4, '') if part['kind'] == 'ink' else (0.6, f' transform="{LOGO_TRANSFORM}"')
            body.append(f'<path {common}fill="{CRIMSON}" stroke="{CRIMSON}" stroke-width="{width}"{extra} '
                        f'{dash_attr} {fill_attr} {ln_attr}>{dash_anim}{fill_anim}{ln_anim}</path>')
    return (f'<g id="coffee-cup-glow" filter="url(#glow)"><g transform="{CUP_TRANSFORM}" fill="none" '
            f'stroke="{CRIMSON}" stroke-width="{glow_w:.1f}" stroke-linejoin="round">{"".join(glow)}</g></g>\n'
            f'    <g id="coffee-cup" transform="{CUP_TRANSFORM}">{"".join(body)}</g>')


def animated_document(items, cup, total, freeze=None):
    defs = ''.join(f'\n    <path id="g-{i["id"]}" d="{i["d"]}"/>' for i in items)
    defs += ''.join('\n    ' + mask_xml(i, total, freeze, g) for i in items for g in (True, False))
    layers = (
        f'<g id="glow" filter="url(#glow)">'
        f'<g fill="{CRIMSON}" stroke="{CRIMSON}" stroke-width="11" stroke-linejoin="round">'
        f'{"".join(glyph_xml(i, True) for i in items)}</g></g>\n'
        f'    <g id="fill" fill="#fff" stroke="#fff" stroke-width="2.6" stroke-linejoin="round">'
        f'{"".join(glyph_xml(i, False) for i in items)}</g>\n'
        f'    {cup_xml(cup, total, freeze)}')
    t = f'translate({W * (1 - INSET) / 2:.2f} {H * (1 - INSET) / 2:.2f}) scale({INSET})'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" role="img" aria-label="The Programmer Diaries">\n'
            f'  <defs>\n    {FILTER}{defs}\n  </defs>\n'
            f'  <g id="artwork" transform="{t}">\n'
            f'   <g id="write-loop">\n    {layers}\n   </g>\n'
            f'  </g>\n</svg>\n')


def main():
    comps = build_components()
    os.makedirs(COMP_DIR, exist_ok=True)
    # Standalone previews: every component shares the banner's canvas, so each
    # one can be opened and edited alone and still lines up with the others.
    for name in ('the', 'programmer', 'diaries', 'coffee-cup'):
        with open(f'{COMP_DIR}/{name}.svg', 'w') as f:
            f.write(document([name], comps, name))
    static = document(['the', 'programmer', 'diaries', 'coffee-cup'], comps, 'The Programmer Diaries')
    open(OUT_STATIC, 'w').write(static)
    items, cup, total = build_items()
    svg = animated_document(items, cup, total)
    open(OUT, 'w').write(svg)
    print(f'static {len(static) // 1024} KB, animated {len(svg) // 1024} KB, loop {total:.1f}s')


if __name__ == '__main__':
    main()
