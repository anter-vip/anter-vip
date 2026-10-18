"""
project_cards.py — generated (not hand-drawn) dark project cards, one SVG per
featured repo: title, one-line value, a real metric, tech tag chips and a
"readme" hint. Geometry (accent bar, corner ticks, tag row) is computed, so
adding a project to PROJECTS is all it takes. README wraps each card in <a>.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    BG, CARD, CYAN, CYAN_DIM, VIOLET, TEXT, MUTED, FAINT, LINE, WIDTH,
    Svg, seed_today,
)

CW, CH = 410, 205   # card size — two fit per 850px row
PAD = 8

# (slug, title, one-liner, metric, [tags], repo url)
PROJECTS = [
    ("cipherquest", "CipherQuest",
     "Interactive cryptography platform — learn ciphers by breaking them.",
     "3 engines · lab · share links",
     ["Next.js", "TypeScript", "React"],
     "https://github.com/anter-vip/cipherquest"),
    ("albasira", "Al-Basira · BI Platform",
     "Arabic-first multi-tenant BI: upload an ERP export, get RTL dashboards.",
     "18 modules · RTL · leak detection",
     ["Python", "Flask", "pandas"],
     "https://github.com/anter-vip/bi-platform"),
    ("joot", "Joot",
     "Motion-design portfolio built on a custom animation engine.",
     "hand-rolled animation lib",
     ["Next.js", "Framer Motion"],
     "https://github.com/anter-vip/joot"),
    ("khayma", "Khayma 3D",
     "Configurable 3D tent product viewer for e-commerce.",
     "webgl · parametric textures",
     ["Three.js", "JavaScript"],
     "https://github.com/anter-vip/khayma-3d"),
]


def wrap(text: str, width_chars: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines[:2]


def card_svg(slug, title, one_liner, metric, tags, url, seed) -> str:
    svg = Svg(CW, CH, title=f"{title} project card")
    rng = np.random.default_rng(abs(hash(slug + str(seed))) % 2**32)
    svg.el(f'<rect width="{CW}" height="{CH}" rx="14" fill="{CARD}"'
           f' stroke="{LINE}" stroke-width="1"/>')
    # accent bar with seeded gradient stop position (subtle daily variance)
    g = svg.lg([(0, CYAN), (rng.uniform(0.5, 0.9), VIOLET), (1, "#0B0B0F")])
    svg.el(f'<rect x="0" y="0" width="{CW}" height="4" rx="2" fill="{g}"/>')
    # corner ticks (blueprint marks), computed
    for (tx, ty, dx, dy) in [(CW - 26, 22, 1, 0), (CW - 26, 22, 0, 1)]:
        svg.el(f'<line x1="{tx}" y1="{ty}" x2="{tx + dx * 12}" y2="{ty + dy * 12}"'
               f' stroke="{CYAN_DIM}" stroke-width="1.4"/>')
    svg.el(svg.text(20, 42, title, 17, TEXT, weight="700", spacing=0.5))
    y = 66
    for ln in wrap(one_liner, 46):
        svg.el(svg.text(20, y, ln, 11, MUTED))
        y += 17
    # metric row
    svg.el(f'<line x1="20" y1="{y + 8}" x2="{CW - 20}" y2="{y + 8}" stroke="{LINE}"/>')
    svg.el(svg.text(20, y + 30, "// " + metric, 10.5, CYAN, spacing=0.5))
    # tag chips, widths computed from text
    tx = 20
    for t in tags:
        w = len(t) * 6.4 + 16
        if tx + w > CW - 20:
            break
        svg.el(f'<rect x="{tx}" y="{CH - 52}" width="{w:.0f}" height="20" rx="5"'
               f' fill="#101018" stroke="{LINE}"/>')
        svg.el(svg.text(tx + 8, CH - 38, t, 9.5, FAINT))
        tx += w + 7
    # hover hint
    svg.el(svg.text(CW - 20, CH - 20, "↗ readme", 10, FAINT, anchor="end"))
    return svg.tostring()


def build_all() -> None:
    seed = seed_today(salt=8)
    here = os.path.dirname(os.path.abspath(__file__))
    for p in PROJECTS:
        out = os.path.join(here, "..", "assets", f"card-{p[0]}.svg")
        with open(out, "w") as f:
            f.write(card_svg(*p, seed))
        print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")


if __name__ == "__main__":
    build_all()
