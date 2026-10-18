"""
hero_flowfield.py — full-width hero: a real Perlin-noise flow field computed
in Python, particle paths traced through it, drawn as self-animating trails.
Name sits centered with a stacked-layer glitch effect.

Algorithm (not faked):
  1. Perlin2D(seed=today) -> angle field theta(x,y) = noise * 2pi * 2
  2. Euler-integrate ~160 particles through the field, sampling every ~16 px
  3. Emit each trajectory as a <path pathLength=100> and animate stroke-dashoffset
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    CYAN, VIOLET, TEXT, MUTED, FAINT, WIDTH, FONT,
    Svg, frame, esc, perlin2d, seed_today, trail_classes,
)

H = 340
N_PARTICLES = 130      # tuned for ~80 KB file — GitHub renders SVG-as-img smoothly
N_GROUPS = 8
DUR = 14.0  # seconds per trail cycle


def trace_paths(seed: int) -> list[str]:
    """Integrate particles through the Perlin angle field; return SVG path 'd' strings."""
    noise = perlin2d(seed)
    rng = np.random.default_rng(seed)
    h = 8.0                      # euler step
    step_sample = 2              # record a point every 2 integration steps
    max_steps = 56

    paths = []
    for _ in range(N_PARTICLES):
        x = float(rng.uniform(-40, WIDTH + 40))
        y = float(rng.uniform(-20, H + 20))
        pts = [(x, y)]
        for s in range(max_steps):
            # noise scale 0.006 -> smooth large swirls; two octaves for detail
            t = (noise(x * 0.006, y * 0.006) + 0.4 * noise(x * 0.015, y * 0.015)) * np.pi * 2
            x += h * np.cos(t)
            y += h * np.sin(t)
            if not (-80 < x < WIDTH + 80 and -60 < y < H + 60):
                break
            if (s + 1) % step_sample == 0:
                pts.append((x, y))
        if len(pts) < 5:
            continue
        # quadratic-smoothed polyline
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
        for (px, py), (cx, cy) in zip(pts[:-2], pts[1:-1]):
            d += f" Q {cx:.1f} {cy:.1f} {(cx + px) / 2:.1f} {(cy + py) / 2:.1f}"
        d += f" T {pts[-1][0]:.1f} {pts[-1][1]:.1f}"
        paths.append(d)
    return paths


def build() -> str:
    seed = seed_today(salt=1)
    svg = Svg(WIDTH, H, title="Ahmed Anter — generative flow field hero")
    frame(svg, grid=48)
    svg.style(
        ".name{font-family:%s;font-size:52px;font-weight:700;letter-spacing:10px}" % FONT
    )
    # glitch layers: same text, offset tints, jitter via keyframes
    svg.style(
        """
@keyframes glitchA{0%,58%,100%{transform:translate(0,0);opacity:0}
 60%{transform:translate(-3px,1px);opacity:.55}64%{transform:translate(2px,-1px);opacity:.4}
 66%{transform:translate(0,0);opacity:0}}
@keyframes glitchB{0%,78%,100%{transform:translate(0,0);opacity:0}
 80%{transform:translate(3px,-2px);opacity:.5}84%{transform:translate(-2px,1px);opacity:.35}
 87%{transform:translate(0,0);opacity:0}}
.gA{animation:glitchA 5.5s steps(1,end) infinite}
.gB{animation:glitchB 5.5s steps(1,end) infinite}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:.8}}
.sub{animation:pulse 4s ease-in-out infinite}
"""
    )

    grad = svg.lg([(0.0, CYAN), (0.65, CYAN), (1.0, VIOLET)])
    paths = trace_paths(seed)
    per_group = max(1, len(paths) // N_GROUPS)
    body = []
    for i, d in enumerate(paths):
        g_cls = (i // per_group) % N_GROUPS
        w = 0.7 + (i % 4) * 0.35
        o = 0.35 + (i % 3) * 0.12
        body.append(
            f'<path class="tr{g_cls}" d="{d}" pathLength="100" fill="none"'
            f' stroke="{grad}" stroke-width="{w:.1f}" stroke-linecap="round"'
            f' opacity="{o:.2f}" stroke-dasharray="100"/>'
        )
    trail_classes(svg, N_GROUPS, DUR)
    svg.el("".join(body))

    # centered name with glitch ghosts
    cx, cy = WIDTH / 2, H / 2 + 6
    name = "AHMED ANTER"
    svg.el(
        f'<text class="name gB" x="{cx}" y="{cy}" text-anchor="middle"'
        f' fill="{VIOLET}" style="mix-blend-mode:screen">{name}</text>'
        f'<text class="name gA" x="{cx}" y="{cy}" text-anchor="middle"'
        f' fill="{CYAN}" style="mix-blend-mode:screen">{name}</text>'
        f'<text class="name" x="{cx}" y="{cy}" text-anchor="middle" fill="{TEXT}">'
        f"{name}</text>"
    )
    svg.el(
        svg.text(cx, cy + 42, "DATA ANALYST · SOFTWARE DEVELOPER", 13, MUTED,
                 anchor="middle", spacing=6, attrs='class="sub"')
    )
    svg.el(
        svg.text(28, H - 20, f"// perlin flow field · {len(paths)} particle traces"
                 f" · seed {seed}", 10, FAINT, spacing=1)
    )
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "hero.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
