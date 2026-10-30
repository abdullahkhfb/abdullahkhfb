"""Builds assets/banner.svg in the style of the English Apothecary Diaries logo
(assets/source/title-en.png): same 602x310 aspect ratio and the same stacked
layout (small "The", large middle word, "Diaries" with the coffee-cup at its left).

Each piece (The / Programmer / Diaries / coffee cup) is also written on its own to
assets/components/ so it can be previewed and tuned in isolation.

Everything is vector: lettering is converted to outlines from Black Chancery
and the coffee-cup is drawn as paths, so nothing is raster and nothing is cropped
at any zoom level.

Usage: python3 scripts/build_banner.py
"""
import os

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = 'assets/banner.svg'
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


def main():
    comps = build_components()
    os.makedirs(COMP_DIR, exist_ok=True)
    # Standalone previews: every component shares the banner's canvas, so each
    # one can be opened and edited alone and still lines up with the others.
    for name in ('the', 'programmer', 'diaries', 'coffee-cup'):
        with open(f'{COMP_DIR}/{name}.svg', 'w') as f:
            f.write(document([name], comps, name))
    svg = document(['the', 'programmer', 'diaries', 'coffee-cup'], comps, 'The Programmer Diaries')
    open(OUT, 'w').write(svg)
    print(len(svg) // 1024, 'KB')


main()
