"""Computes a handwriting "pen path" for every letter of the banner.

The font only contains outlines, so a pen path has to be derived from the shapes: each letter is
rasterised at high resolution, reduced to its centre line (the medial axis, i.e. the line a
broad-nib pen would follow), cleaned of the little spurs that sharp corners create, and then walked
the way a hand would: a stroke keeps going through a junction in the direction that bends least,
and the pen lifts only when there is nothing left to continue into.

For every stroke it records points (x, y, r) in banner coordinates, where r is the radius of the
largest circle that fits inside the letter at that point, so a nib of that size covers the letter
exactly. build_banner.py turns these into the animation; nothing here needs to run again unless
the lettering changes.

Needs: pip install numpy scipy scikit-image skan svgpathtools
Usage (from the repository root): python3 scripts/trace_pen_paths.py
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi
from skan import Skeleton, summarize
from skimage.draw import disk, polygon as fill_polygon
from skimage.morphology import skeletonize
from svgpathtools import parse_path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_banner as bb  # noqa: E402

OUT = 'assets/source/pen_paths.json'
S = 8               # raster pixels per banner unit
MARGIN = 6          # blank border (units) around each glyph in its raster
SPACING = 1.5       # units between stored points along a stroke
SMOOTH = 1.3        # gaussian smoothing of a stroke, in samples
MAX_TURN = 115      # degrees; a stroke does not continue through a bend sharper than this
SPUR_FACTOR = 2.2   # branches shorter than SPUR_FACTOR * local radius (+ SPUR_BASE) are spur candidates
SPUR_BASE = 3.0
NIB_GROW = 1.12     # the nib is this much wider than the inscribed circle...
NIB_PAD = 0.6       # ...plus this many units, so corners are never left uncovered


# ------------------------------------------------------------------ raster ----
def rasterise(d, box):
    """Filled raster of a glyph outline (non-zero winding, counters stay open)."""
    ox, oy = box[0] - MARGIN, box[1] - MARGIN
    w = int((box[2] - box[0] + 2 * MARGIN) * S) + 1
    h = int((box[3] - box[1] + 2 * MARGIN) * S) + 1
    winding = np.zeros((h, w), int)
    for sub in parse_path(d).continuous_subpaths():
        pts = []
        for seg in sub:
            n = 2 if seg.__class__.__name__ == 'Line' else 24
            pts += [seg.point(t) for t in np.linspace(0, 1, n, endpoint=False)]
        xs = np.array([(p.real - ox) * S for p in pts])
        ys = np.array([(p.imag - oy) * S for p in pts])
        area = 0.5 * np.sum(xs * np.roll(ys, -1) - np.roll(xs, -1) * ys)
        rr, cc = fill_polygon(ys, xs, winding.shape)
        part = np.zeros_like(winding)
        part[rr, cc] = 1
        winding += (1 if area > 0 else -1) * part
    return winding != 0, ox, oy


# ------------------------------------------------------------------ helpers ----
def arclen(pts):
    return np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])


def away_vector(pts, end, reach=5.0):
    """Unit vector pointing from the given end of an edge into the edge."""
    p = pts if end == 's' else pts[::-1]
    s = arclen(p)
    k = int(np.searchsorted(s, min(reach, s[-1]))) if s[-1] > 0 else 1
    v = p[min(max(k, 1), len(p) - 1)] - p[0]
    n = np.hypot(*v)
    return v / n if n else np.array([1.0, 0.0])


def turning(travel, leave):
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(travel, leave))))))


def resample(pts, spacing):
    s = arclen(pts)
    if s[-1] < 1e-6:
        return pts[:1]
    n = max(2, int(round(s[-1] / spacing)) + 1)
    u = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(u, s, pts[:, 0]), np.interp(u, s, pts[:, 1])])


# ----------------------------------------------------------- skeleton graph ----
class Edge:
    def __init__(self, src, dst, pts):
        self.src, self.dst, self.pts = src, dst, pts
        self.spur = False

    @property
    def length(self):
        return arclen(self.pts)[-1]


def skeleton_edges(sk, ox, oy, dt):
    skel = Skeleton(sk)
    table = summarize(skel, separator='-')
    edges = []
    for i in range(skel.n_paths):
        c = skel.path_coordinates(i).astype(float)
        pts = np.column_stack([c[:, 1] / S + ox, c[:, 0] / S + oy])
        edges.append(Edge(int(table['node-id-src'][i]), int(table['node-id-dst'][i]), pts))
    return edges


def mark_spurs(edges, dt, ox, oy):
    """Flag short dead-end branches: corner artefacts of the skeleton rather than real strokes."""
    count = {}
    for e in edges:
        for n in (e.src, e.dst):
            count[n] = count.get(n, 0) + 1
    for e in edges:
        free_src, free_dst = count[e.src] == 1 and e.src != e.dst, count[e.dst] == 1 and e.src != e.dst
        if free_src == free_dst:            # both free (isolated stroke) or both joined: not a spur
            continue
        joint = e.dst if free_src else e.src
        jp = e.pts[-1] if free_src else e.pts[0]
        r = dt[int((jp[1] - oy) * S), int((jp[0] - ox) * S)] / S
        if e.length < SPUR_FACTOR * r + SPUR_BASE:
            e.spur = True


# ------------------------------------------------------------- stroke walk ----
def walk(edges, start_hint):
    """Join edges into strokes (lists of points) in a handwriting-like order."""
    inc = {}
    for k, e in enumerate(edges):
        inc.setdefault(e.src, []).append((k, 's'))
        inc.setdefault(e.dst, []).append((k, 'd'))
    visited, strokes, pen = set(), [], None

    def node_of(k, end):
        return edges[k].src if end == 's' else edges[k].dst

    def free_degree(n):
        return sum(1 for k, _ in inc[n] if k not in visited)

    while len(visited) < len(edges):
        starts = []
        for k, e in enumerate(edges):
            if k in visited:
                continue
            for end in ('s', 'd'):
                n = node_of(k, end)
                p = e.pts[0] if end == 's' else e.pts[-1]
                tip = free_degree(n) == 1
                inked = any(j in visited for j, _ in inc[n])
                starts.append((k, end, p, tip, inked))
        tips = [c for c in starts if c[3]] or starts
        if pen is None:
            best = min(tips, key=lambda c: start_hint(c[2]))
        else:      # continue from existing ink if possible, otherwise from the nearest free tip
            best = min(tips, key=lambda c: math.dist(pen, c[2]) - (30 if c[4] else 0))
        k, end = best[0], best[1]
        stroke = []
        while True:
            e = edges[k]
            pts = e.pts if end == 's' else e.pts[::-1]
            stroke.append(pts)
            visited.add(k)
            node = e.dst if end == 's' else e.src
            travel = -away_vector(e.pts, 'd' if end == 's' else 's')
            options = []
            for j, jend in inc[node]:
                if j in visited:
                    continue
                turn = turning(travel, away_vector(edges[j].pts, jend))
                if turn <= MAX_TURN:
                    options.append((turn, j, jend))
            if not options:
                break
            _, k, end = min(options)
        poly = np.vstack([stroke[0]] + [s[1:] for s in stroke[1:]])
        strokes.append(poly)
        pen = poly[-1]
    return strokes


def components(edges):
    """Edge indices grouped by connected piece of ink, longest piece first."""
    parent = {}

    def find(n):
        parent.setdefault(n, n)
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for e in edges:
        parent[find(e.src)] = find(e.dst)
    groups = {}
    for k, e in enumerate(edges):
        groups.setdefault(find(e.src), []).append(k)
    return sorted(groups.values(), key=lambda g: -sum(edges[k].length for k in g))


def downward(poly):
    """A mostly vertical stroke is written top to bottom, like a stem."""
    dx, dy = poly[-1] - poly[0]
    return poly[::-1] if dy < 0 and abs(dy) > 1.5 * abs(dx) else poly


def reroot_loop(poly):
    """An isolated closed loop (o, the bowl of a, ...) is started top-right and drawn anticlockwise."""
    pts = poly[:-1] if np.allclose(poly[0], poly[-1]) else poly
    cx = pts[:, 0].mean()
    i = int(np.argmin(pts[:, 1] - 0.35 * (pts[:, 0] - cx)))
    pts = np.roll(pts, -i, axis=0)
    ahead = pts[min(len(pts) - 1, max(2, len(pts) // 30))]
    if ahead[0] > pts[0][0]:                # first moves right: that is clockwise, so reverse
        pts = np.vstack([pts[:1], pts[:0:-1]])
    return np.vstack([pts, pts[:1]])


# ------------------------------------------------------------------ driver ----
def finish_stroke(poly, dt, ox, oy):
    pts = resample(poly, SPACING)
    if len(pts) > 3:
        sm = np.column_stack([ndi.gaussian_filter1d(pts[:, 0], SMOOTH, mode='nearest'),
                              ndi.gaussian_filter1d(pts[:, 1], SMOOTH, mode='nearest')])
        sm[0], sm[-1] = pts[0], pts[-1]
        pts = sm
    rr = (pts[:, 1] - oy) * S
    cc = (pts[:, 0] - ox) * S
    radius = ndi.map_coordinates(dt, [rr, cc], order=1, mode='nearest') / S
    return np.column_stack([pts, radius])


def coverage_gap(strokes_xyr, sm, ox, oy):
    """Raster of letter pixels that no nib position covers."""
    cover = np.zeros(sm.shape, bool)
    for st in strokes_xyr:
        for x, y, r in st:
            rr, cc = disk(((y - oy) * S, (x - ox) * S), (r * NIB_GROW + NIB_PAD) * S, shape=sm.shape)
            cover[rr, cc] = True
    return sm & ~cover


def corner_patches(strokes, gap, ox, oy):
    """Small discs for corners the centre line cannot reach. Each remembers which stroke sample is
    nearest, so it is revealed at the moment the pen passes by."""
    gap = gap.copy()
    patches = []
    flat = [(k, i, x, y) for k, st in enumerate(strokes) for i, (x, y, _) in enumerate(st)]
    while gap.sum() / S ** 2 > 0.15 and len(patches) < 40:
        thick = ndi.distance_transform_edt(gap)
        r0, c0 = np.unravel_index(int(np.argmax(thick)), thick.shape)
        r = thick[r0, c0] / S + 2.4
        x, y = c0 / S + ox, r0 / S + oy
        k, i, _, _ = min(flat, key=lambda f: math.hypot(f[2] - x, f[3] - y))
        patches.append([round(x, 2), round(y, 2), round(r, 2), k, i])
        rr, cc = disk((r0, c0), r * S, shape=gap.shape)
        gap[rr, cc] = False
    return patches


def trace_glyph(ch):
    fill, ox, oy = rasterise(ch['d'], ch['box'])
    sm = ndi.gaussian_filter(fill.astype(float), 1.5) > 0.5
    dt = ndi.distance_transform_edt(sm)
    edges = skeleton_edges(skeletonize(sm), ox, oy, dt)
    mark_spurs(edges, dt, ox, oy)
    x0, y0 = ch['box'][0], ch['box'][1]
    hint = lambda p: (p[1] - y0) + 0.35 * (p[0] - x0)          # top-left first

    def assemble(use):
        chosen = [e for e in edges if e.spur is False or id(e) in use]
        loops = [e for e in chosen if e.src == e.dst and sum(1 for f in chosen if e.src in (f.src, f.dst)) == 1]
        for e in loops:
            e.pts = reroot_loop(e.pts)
        raw = []
        for group in components(chosen):
            raw += walk([chosen[k] for k in group], hint)
        return [finish_stroke(downward(p), dt, ox, oy) for p in raw]

    restored = set()
    strokes = assemble(restored)
    gap = coverage_gap(strokes, sm, ox, oy)
    for _ in range(6):                      # bring spurs back only where letter would go uncovered
        if gap.sum() / S ** 2 < 3.0:
            break
        best, best_gain = None, 0
        for e in edges:
            if e.spur and id(e) not in restored:
                trial = finish_stroke(e.pts, dt, ox, oy)
                gain = (gap & ~coverage_gap([trial], gap, ox, oy)).sum()
                if gain > best_gain:
                    best, best_gain = e, gain
        if best is None or best_gain / S ** 2 < 0.8:
            break
        restored.add(id(best))
        strokes = assemble(restored)
        gap = coverage_gap(strokes, sm, ox, oy)
    patches = corner_patches(strokes, gap, ox, oy)
    return strokes, patches, gap.sum() / S ** 2, sm


def main():
    words = bb.glyph_outlines()
    out = {}
    for word, chars in words.items():
        out[word] = []
        for i, ch in enumerate(chars):
            strokes, patches, gap, _ = trace_glyph(ch)
            length = sum(arclen(s[:, :2])[-1] for s in strokes)
            print(f'{word}[{i}] strokes={len(strokes)} length={length:6.1f} '
                  f'corner patches={len(patches)} (gap before patches {gap:5.2f} u^2)')
            out[word].append({
                'strokes': [[[round(float(x), 2), round(float(y), 2), round(float(r), 2)] for x, y, r in s]
                            for s in strokes],
                'patches': patches})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print('wrote', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
