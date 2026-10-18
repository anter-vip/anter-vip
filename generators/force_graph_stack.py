"""
force_graph_stack.py — a REAL force-directed layout simulated in Python:
Coulomb repulsion between all nodes, Hooke springs along edges, a weak center
gravity and velocity damping. We integrate until convergence, then render the
RELAXED final layout with a gentle per-node float (CSS translate keyframes,
staggered) and softly pulsing edges.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    CARD, CYAN, CYAN_DIM, VIOLET, TEXT, MUTED, FAINT, LINE, WIDTH, FONT,
    Svg, frame, blueprint_label, caption, seed_today,
)

H = 400
CX, CY = WIDTH / 2, H / 2 + 12

# node = (label, tier)   tier 0 = core, 1 = primary, 2 = secondary
NODES = [
    ("data", 0),
    ("Python", 1), ("SQL", 1), ("TypeScript", 1), ("Power BI", 1),
    ("pandas", 2), ("NumPy", 2), ("Flask", 2), ("React", 2), ("Next.js", 2),
    ("Node.js", 2), ("ECharts", 2), ("Excel", 2), ("Git", 2), ("Playwright", 2),
]
EDGES = [
    (0, 1), (0, 2), (0, 3), (0, 4),
    (1, 5), (1, 6), (1, 7), (3, 8), (3, 9), (3, 10),
    (4, 12), (4, 11), (2, 12), (0, 13), (1, 14), (8, 9), (7, 10),
]

REPULSE = 26000.0
SPRING_K = 0.018
SPRING_LEN = 86.0
GRAVITY = 0.012
DAMP = 0.86


def simulate(seed: int, iters: int = 420):
    rng = np.random.default_rng(seed)
    n = len(NODES)
    pos = rng.uniform(-160, 160, (n, 2)) * np.array([1.9, 1.0])
    pos += np.array([CX, CY])
    vel = np.zeros_like(pos)
    for _ in range(iters):
        force = np.zeros_like(pos)
        # Coulomb repulsion (all pairs — n is tiny)
        for i in range(n):
            d = pos[i] - pos
            d2 = (d ** 2).sum(1) + 1e-4
            force[i] += (REPULSE * d / (d2 * np.sqrt(d2))[:, None]).sum(0)
        # Hooke springs
        for a, b in EDGES:
            d = pos[b] - pos[a]
            dist = np.linalg.norm(d) + 1e-6
            f = SPRING_K * (dist - SPRING_LEN) * d / dist
            force[a] += f
            force[b] -= f
        # center gravity + damping
        force += -GRAVITY * (pos - np.array([CX, CY]))
        vel = (vel + force) * DAMP
        vel = np.clip(vel, -6, 6)
        pos += vel
    # README <img> hides overflow — clamp the relaxed layout inside the canvas
    pos[:, 0] = np.clip(pos[:, 0], 46, WIDTH - 46)
    pos[:, 1] = np.clip(pos[:, 1], 74, H - 56)
    return pos


def build() -> str:
    seed = seed_today(salt=7)
    pos = simulate(seed)
    svg = Svg(WIDTH, H, title="tech stack force-directed graph")
    frame(svg, grid=48)
    blueprint_label(svg, 28, 30, "02 — STACK PHYSICS")
    svg.el(svg.text(WIDTH - 28, 30, "coulomb + hooke + damping · relaxed in python",
                    10, FAINT, anchor="end", spacing=1))

    # float keyframes — two shared animations, nodes pick delay by index
    svg.style(
        """
@keyframes floatA{0%,100%{transform:translate(0,0)}50%{transform:translate(0,-7px)}}
@keyframes floatB{0%,100%{transform:translate(0,0)}50%{transform:translate(0,6px)}}
@keyframes edgePulse{0%,100%{stroke-opacity:.22}50%{stroke-opacity:.6}}
.nd{animation:floatA 6s ease-in-out infinite}
.nd2{animation:floatB 7.4s ease-in-out infinite}
.ed{animation:edgePulse 5s ease-in-out infinite}
"""
    )

    # edges first (under nodes)
    for i, (a, b) in enumerate(EDGES):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        col = svg.lg([(0, CYAN_DIM), (1, VIOLET)]) if i % 3 == 0 else CYAN_DIM
        svg.el(
            f'<line class="ed" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
            f' stroke="{col}" stroke-width="{1.4 if a == 0 or b == 0 else 0.9}"'
            f' style="animation-delay:{-i * 0.45:.2f}s"/>'
        )

    # nodes
    for i, (label, tier) in enumerate(NODES):
        x, y = pos[i]
        r = {0: 30, 1: 21, 2: 14}[tier]
        fill = {0: "#0E2E33", 1: CARD, 2: "#0D0D14"}[tier]
        stroke = {0: CYAN, 1: CYAN_DIM, 2: LINE}[tier]
        fsize = {0: 13, 1: 10, 2: 8.5}[tier]
        cls = "nd" if i % 2 else "nd2"
        delay = -(i * 0.62) % 6
        inner = (
            f'<circle r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
            + (f'<circle r="{r + 6}" fill="none" stroke="{CYAN}" stroke-width="0.6"'
               f' opacity="0.35"/>' if tier == 0 else "")
            + svg.text(0, fsize / 3 - 1, label, fsize,
                        TEXT if tier < 2 else MUTED, anchor="middle",
                        weight="bold" if tier == 0 else "normal")
        )
        # outer g = attribute transform (layout), inner g = CSS float animation.
        # CSS transform would OVERRIDE the transform attribute, so they never
        # share an element.
        svg.el(
            f'<g transform="translate({x:.1f} {y:.1f})">'
            f'<g class="{cls}" style="animation-delay:{delay:.2f}s">{inner}</g></g>'
        )

    svg.el(svg.text(28, H - 52, f"// layout seed {seed}", 9, FAINT))
    caption(svg, "// the graph you see is where the physics settled — nothing hand-placed")
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "stack-graph.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
