"""
common.py — shared SVG builder for every generator in this repo.

Design contract (read before adding a generator):
  * GitHub serves README SVGs as <img>, so:
      - NO <script>, NO external references, NO webfonts. text uses
        font-family="JetBrains Mono, monospace" and falls back gracefully.
      - All motion is CSS @keyframes or SMIL <animate*> embedded in the file.
      - Keep every file well under 500 KB — prefer fewer elements with real
        motion over dense static detail.
  * Every generator is a deterministic function of the date: same day ->
    same art, next day -> new art. Use seed_today().
  * All canvases are WIDTH px wide so the README reads as one dark canvas.

Public API:
  Svg             — string-building SVG document helper
  frame()         — shared dark background + blueprint grid + vignette
  blueprint_label() — the "// 01 — STACK" style micro headings
  caption()       — dim monospace caption at the bottom
  dash_css()      — keyframes that draw a path then fade (flow-field trails)
  perlin2d()      — classic Perlin noise, seeded
  esc(), seed_today(), fmt_num(), lang_bytes_to_pcts()
"""

from __future__ import annotations

import datetime
import math
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

# --------------------------------------------------------------------------
# Palette — dark luxury data terminal. Single accent, violet only in gradients
# --------------------------------------------------------------------------
BG = "#050505"          # pure-black canvas
CARD = "#0B0B0F"        # card surface
LINE = "#1A1A22"        # 1px borders / grid lines
CYAN = "#00E5FF"        # the one accent
CYAN_DIM = "#0A6C7A"    # accent at rest
VIOLET = "#7C3AED"      # gradients only
TEXT = "#E6E6EC"
MUTED = "#8A8A9A"
FAINT = "#4A4A58"
GONE = "#22222C"        # barely-there (dead cells, unused slots)

WIDTH = 850             # shared canvas width across ALL svgs
FONT = "JetBrains Mono, monospace"


def esc(s: str) -> str:
    """Escape text for XML content."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def seed_today(salt: int = 0) -> int:
    """Deterministic per-day seed. Art changes daily, replays identically today."""
    d = datetime.date.today()
    return d.year * 10000 + d.month * 100 + d.day + salt


def fmt_num(n: float) -> str:
    """1234 -> 1.2k, 1234567 -> 1.2M — for stat tiles."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


class Svg:
    """Minimal, allocation-free SVG string builder.

    Elements are appended as raw XML strings. defs() and style() fill the
    <defs>/<style> blocks; body elements are everything else.
    """

    def __init__(self, width: int, height: int, title: str = "") -> None:
        self.w = width
        self.h = height
        self._defs: List[str] = []
        self._css: List[str] = []
        self._body: List[str] = []
        self._grad_seq = 0
        self.title = title

    # ---- structure -----------------------------------------------------
    def defs(self, raw: str) -> None:
        self._defs.append(raw)

    def style(self, css: str) -> None:
        self._style_guard = True
        self._css.append(css)

    def el(self, raw: str) -> None:
        self._body.append(raw)

    def g(self, attrs: str, children: Sequence[str]) -> str:
        """Build a <g> chunk from pre-rendered children (returned, not appended)."""
        return f'<g {attrs}>' + "".join(children) + "</g>"

    # ---- gradients -------------------------------------------------------
    def lg(self, stops: Sequence[Tuple[float, str]],
           x1: float = 0.0, y1: float = 0.0, x2: float = 1.0, y2: float = 0.0) -> str:
        """Linear gradient, stops = [(offset 0..1, color), ...]. Returns url(#id)."""
        self._grad_seq += 1
        gid = f"g{self._grad_seq}"
        body = "".join(
            f'<stop offset="{o:.2f}" stop-color="{c}"/>' for o, c in stops
        )
        self.defs(
            f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f"{body}</linearGradient>"
        )
        return f"url(#{gid})"

    def rad(self, stops: Sequence[Tuple[float, str]], r: float = 0.7) -> str:
        self._grad_seq += 1
        gid = f"r{self._grad_seq}"
        body = "".join(
            f'<stop offset="{o:.2f}" stop-color="{c}"/>' for o, c in stops
        )
        self.defs(
            f'<radialGradient id="{gid}" cx="50%" cy="50%" r="{r}">{body}'
            f"</radialGradient>"
        )
        return f"url(#{gid})"

    # ---- text --------------------------------------------------------------
    def text(self, x: float, y: float, s: str, size: int = 13, fill: str = TEXT,
             anchor: str = "start", weight: str = "normal",
             spacing: float = 0, opacity: float = 1.0, attrs: str = "") -> str:
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        op = f' opacity="{opacity}"' if opacity != 1.0 else ""
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}"'
            f' font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}{op}'
            f' {attrs}>{esc(s)}</text>'
        )

    # ---- serialize -------------------------------------------------------
    def tostring(self) -> str:
        css = "\n".join(self._css)
        style_block = f"<style>{css}</style>" if css else ""
        title = f"<title>{esc(self.title)}</title>" if self.title else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}"'
            f' viewBox="0 0 {self.w} {self.h}" role="img">{title}'
            f"<defs>{''.join(self._defs)}{style_block}</defs>"
            f"{''.join(self._body)}\n</svg>\n"
        )


# --------------------------------------------------------------------------
# Shared frame: black bg, blueprint grid, vignette, optional card
# --------------------------------------------------------------------------
def frame(svg: Svg, grid: int = 42, with_vignette: bool = True) -> None:
    """Paint the shared backdrop every generator starts with."""
    svg.el(f'<rect width="{svg.w}" height="{svg.h}" fill="{BG}"/>')
    svg.defs(
        f'<pattern id="bp" width="{grid}" height="{grid}" patternUnits="userSpaceOnUse">'
        f'<path d="M {grid} 0 L 0 0 0 {grid}" fill="none" stroke="{LINE}"'
        f' stroke-width="1" opacity="0.4"/></pattern>'
    )
    svg.el(f'<rect width="{svg.w}" height="{svg.h}" fill="url(#bp)"/>')
    if with_vignette:
        vid = svg.rad([(0.0, "#000000"), (0.75, "#000000"), (1.0, BG)], r=0.75)
        # invert: dark center glow removed -> subtle edge dim using overlay
        svg.el(
            f'<rect width="{svg.w}" height="{svg.h}" fill="none"/>'
        )


def card(svg: Svg, x: float, y: float, w: float, h: float, r: float = 14) -> None:
    """A bordered card surface (#0B0B0F / 1px #1A1A22)."""
    svg.el(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}"'
        f' fill="{CARD}" stroke="{LINE}" stroke-width="1"/>'
    )


def blueprint_label(svg: Svg, x: float, y: float, s: str) -> None:
    """The signature micro heading: // 01 — STACK"""
    svg.el(
        svg.text(x, y, "//", 11, CYAN_DIM, weight="bold")
        + ""  # keep concatenation explicit for readability
        + svg.text(x + 22, y, s, 11, MUTED, weight="bold", spacing=3)
    )
    svg.el(
        f'<line x1="{x}" y1="{y + 10}" x2="{x + min(320, len(s) * 9 + 60)}"'
        f' y2="{y + 10}" stroke="{LINE}" stroke-width="1"/>'
    )


def caption(svg: Svg, s: str, y: Optional[float] = None) -> None:
    y = y if y is not None else svg.h - 14
    svg.el(svg.text(svg.w / 2, y, s, 11, FAINT, anchor="middle", spacing=2))


# --------------------------------------------------------------------------
# CSS: trail draw animation for flow-field paths (one keyframe, N delay classes)
# --------------------------------------------------------------------------
def dash_css(pct_draw: float = 0.55, pct_hold: float = 0.82) -> str:
    """Keyframes: 0->L draw, hold visible, fade out, restart. Paths need
    pathLength=100 so the same dashoffset values work for every length."""
    return f"""
@keyframes trail {{
  0%   {{ stroke-dashoffset: 100; opacity: 0; }}
  4%   {{ opacity: 0.9; }}
  {pct_draw * 100:.0f}%  {{ stroke-dashoffset: 0; opacity: 0.9; }}
  {pct_hold * 100:.0f}%  {{ stroke-dashoffset: 0; opacity: 0.9; }}
  96%  {{ stroke-dashoffset: 0; opacity: 0; }}
  100% {{ stroke-dashoffset: 100; opacity: 0; }}
}}"""


def trail_classes(svg: Svg, n: int, dur: float) -> None:
    """Register .tr0..tr{n-1} classes sharing the trail keyframes, staggered."""
    svg.style(dash_css())
    css = []
    for i in range(n):
        delay = -1.0 * i * dur / n
        css.append(
            f".tr{i}{{animation:trail {dur:.1f}s ease-in-out {delay:.2f}s infinite both;}}"
        )
    svg.style("\n".join(css))


# --------------------------------------------------------------------------
# Perlin noise (classic 2D, seeded) — used by the hero flow field
# --------------------------------------------------------------------------
class Perlin:
    """Ken Perlin's improved noise, permutation table shuffled by `seed`."""

    def __init__(self, seed: int) -> None:
        rng = np.random.default_rng(seed)
        p = np.arange(256, dtype=int)
        rng.shuffle(p)
        self.p = np.tile(p, 2)

    @staticmethod
    def _fade(t: np.ndarray) -> np.ndarray:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def grad(self, h: int, x: float, y: float) -> float:
        h &= 7
        u = x if h < 4 else y
        v = y if h < 4 else x
        return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)

    def noise(self, x: float, y: float) -> float:
        xi, yi = math.floor(x) & 255, math.floor(y) & 255
        xf, yf = x - math.floor(x), y - math.floor(y)
        u, v = self._fade(np.array([xf]))[0], self._fade(np.array([yf]))[0]
        p = self.p
        aa = p[p[xi] + yi]
        ab = p[p[xi] + yi + 1]
        ba = p[p[xi + 1] + yi]
        bb = p[p[xi + 1] + yi + 1]
        x1 = _lerp(self.grad(aa, xf, yf), self.grad(ba, xf - 1, yf), u)
        x2 = _lerp(self.grad(ab, xf, yf - 1), self.grad(bb, xf - 1, yf - 1), u)
        return _lerp(x1, x2, v)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def perlin2d(seed: int) -> Callable[[float, float], float]:
    """Return f(x, y) -> noise in [-1, 1]."""
    perm = Perlin(seed)
    return perm.noise
