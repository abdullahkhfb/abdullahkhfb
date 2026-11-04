"""Builds assets/banner.svg in the style of the English Apothecary Diaries logo
(assets/source/title-en.png): same 602x310 aspect ratio and the same stacked
layout (small "The", large middle word, "Diaries" with the coffee-cup at its left).

Each piece (The / Programmer / Diaries / coffee cup) is also written on its own to
assets/components/ so it can be previewed and tuned in isolation.

Everything is vector: lettering is converted to outlines from Black Chancery
and the coffee-cup is drawn as paths, so nothing is raster and nothing is cropped
at any zoom level.

Besides the static banner (assets/banner-static.svg) it writes assets/banner.svg, a
looping "handwriting" version: every character is revealed left to right by its own
soft-edged mask (pure SVG/SMIL, no scripts, so it also plays inside a GitHub <img>).

Usage: python3 scripts/build_banner.py
"""
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
SOFT = 16        # px width of the feathered leading edge of the "pen"
PAD = 10         # reveal margin around a glyph so its stroke + glow are never cut
REACH = 700      # length of the reveal bar (must exceed the widest glyph + SOFT)
MARGIN = 80      # masks reach this far past the canvas so nothing at the edges is clipped
SPEED = 360      # px of lettering written per second
BASE = 0.12      # extra seconds per glyph so narrow letters don't flash in
OVERLAP = 0.08   # next glyph / part starts this long before the previous one ends
WORD_PAUSE = 0.12
LEAD_IN = 0.25   # blank time at the start of every loop
HOLD = 2.0       # finished banner stays on screen before it un-writes
GAP = 0.2        # blank time after un-writing, before the next pass
MIRROR_AT = 0.0  # set by build_items(): time t on the way in <-> MIRROR_AT - t on the way out
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
    return f'{v:.5f}'.rstrip('0').rstrip('.')


def smooth(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def sample(pts, t):
    """Value of a (seconds, value) track at time t, eased between points, held outside them."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * smooth((t - t0) / (t1 - t0))
    return pts[-1][1]


def pingpong(pts):
    """Forward points followed by the same points played backwards (pen retracing its path)."""
    return pts + [(MIRROR_AT - t, v) for t, v in reversed(pts)]


def splines_for(vals):
    return ';'.join(LINEAR if vals[i] == vals[i + 1] else EASE for i in range(len(vals) - 1))


def track(attr, pts, total, freeze):
    """Animate one attribute: along pts = [(seconds, value), ...] and then back again, looping every
    `total` seconds. Returns (static_attr, animate_xml); the static attribute holds the *finished*
    value so renderers without SMIL show the completed banner. freeze=t returns that instant."""
    full = pingpong(pts)
    if freeze is not None:
        return f'{attr}="{fmt(sample(full, freeze))}"', ''
    keys = [0.0] + [t / total for t, _ in full] + [1.0]
    vals = [full[0][1]] + [v for _, v in full] + [full[-1][1]]
    xml = (f'<animate attributeName="{attr}" dur="{total:.2f}s" repeatCount="indefinite" '
           f'calcMode="spline" keyTimes="{";".join(fmt(k) for k in keys)}" '
           f'values="{";".join(fmt(v) for v in vals)}" keySplines="{splines_for(vals)}"/>')
    return f'{attr}="{fmt(pts[-1][1])}"', xml


def build_items():
    """Writing order: The, Programmer, coffee cup (part by part), Diaries."""
    latin = TTFont(LATIN_FONT)
    words = {
        'the': outline_chars(latin, 'The', 66, 24, 51),
        'programmer': outline_chars(latin, 'Programmer', 108, CODING_X, 156, 0),
        'diaries': outline_chars(latin, 'Diaries', 138, 168, 295, 0),
    }
    items, cup, t = [], [], LEAD_IN
    for name in ('the', 'programmer', 'cup', 'diaries'):
        if name == 'cup':
            for pid, kind, d, dur in CUP_SEQ:
                cup.append({'id': pid, 'kind': kind, 'd': d, 'start': t, 'dur': dur})
                t += dur - OVERLAP
            t += OVERLAP + WORD_PAUSE
            continue
        for i, ch in enumerate(words[name]):
            x0, _, x1, _ = ch['box']
            dur = BASE + (x1 - x0) / SPEED
            items.append({'id': f'{name}-{i}', 'd': ch['d'], 'box': ch['box'],
                          'start': t, 'dur': dur,
                          'hide': x0 - PAD - REACH,             # bar fully left of the glyph
                          'show': x1 + PAD - REACH + SOFT})     # solid part of the bar past the glyph
            t += dur - OVERLAP
        t += WORD_PAUSE
    global MIRROR_AT
    written = max(i['start'] + i['dur'] for i in items + cup) + 0.35   # +0.35: last fills settle
    MIRROR_AT = 2 * written + HOLD
    return items, cup, MIRROR_AT + GAP


def mask_xml(it, total, freeze):
    pts = [(it['start'], it['hide']), (it['start'] + it['dur'], it['show'])]
    full = pingpong(pts)
    if freeze is None:
        keys = [0.0] + [t / total for t, _ in full] + [1.0]
        xs = [full[0][1]] + [v for _, v in full] + [full[-1][1]]
        anim = (f'<animateTransform attributeName="transform" type="translate" dur="{total:.2f}s" '
                f'repeatCount="indefinite" calcMode="spline" keyTimes="{";".join(fmt(k) for k in keys)}" '
                f'values="{";".join(f"{x:.1f} 0" for x in xs)}" keySplines="{splines_for(xs)}"/>')
        tx = it['show']          # without SMIL support the text simply shows, fully written
    else:
        anim, tx = '', sample(full, freeze)
    return (f'<mask id="m-{it["id"]}" maskUnits="userSpaceOnUse" x="{-MARGIN}" y="{-MARGIN}" '
            f'width="{W + 2 * MARGIN}" height="{H + 2 * MARGIN}">'
            f'<rect y="{-MARGIN}" width="{REACH}" height="{H + 2 * MARGIN}" fill="url(#edge)" '
            f'transform="translate({tx:.1f} 0)">{anim}</rect></mask>')


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
    defs += (f'\n    <linearGradient id="edge" gradientUnits="userSpaceOnUse" '
             f'x1="{REACH - SOFT}" y1="0" x2="{REACH}" y2="0">'
             f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             f'</linearGradient>')
    defs += ''.join('\n    ' + mask_xml(i, total, freeze) for i in items)

    glow = ''.join(f'<g mask="url(#m-{i["id"]})"><use href="#g-{i["id"]}"/></g>' for i in items)
    layers = (
        f'<g id="glow" filter="url(#glow)">'
        f'<g fill="{CRIMSON}" stroke="{CRIMSON}" stroke-width="11" stroke-linejoin="round">{glow}</g></g>\n'
        f'    <g id="fill" fill="#fff" stroke="#fff" stroke-width="2.6" stroke-linejoin="round">{glow}</g>\n'
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
