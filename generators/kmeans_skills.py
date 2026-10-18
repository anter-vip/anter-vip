"""
kmeans_skills.py — runs REAL Lloyd's K-Means in numpy on 2-D skill points,
records every iteration (assignments + centroid moves), then replays the whole
convergence as an SMIL animation: points recolour to their cluster, centroids
glide iteration by iteration, and finally cluster labels fade in. Loops.

"# mean  of  the  cluster" — the math is not decorative, it is the animation.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    CARD, LINE, CYAN, TEXT, MUTED, FAINT, GONE, WIDTH,
    Svg, frame, blueprint_label, caption, seed_today,
)

H = 360
LOOP = 11.0
ITER_DUR = 1.0          # seconds per kmeans iteration segment
SETTLE = 1.4            # hold time on final state before labels
PAD = 40

CLUSTERS = [
    ("DATA", CYAN, ["Python", "Pandas", "NumPy", "SQL", "Power BI", "Excel", "Statistics"]),
    ("DEV", "#3B82F6", ["TypeScript", "React", "Next.js", "Node.js", "Flask", "HTML/CSS"]),
    ("ML", "#A78BFA", ["scikit-learn", "NLP", "Feature Eng.", "Vision Basics"]),
]
K = len(CLUSTERS)


def kmeans(pts: np.ndarray, rng: np.random.Generator, max_iter: int = 12):
    """Textbook Lloyd's algorithm. Returns (final_labels, history).
    history[i] = (labels_before_iter_i, centroids_before_iter_i)."""
    centroids = pts[rng.choice(len(pts), K, replace=False)].copy()
    history = []
    labels = np.full(len(pts), -1)
    for _ in range(max_iter):
        d = ((pts[:, None, :] - centroids[None, :, :]) ** 2).sum(-1)
        new_labels = d.argmin(1)
        history.append((labels.copy(), centroids.copy()))
        if (new_labels == labels).all() and _ > 0:
            break
        labels = new_labels
        for k in range(K):
            if (labels == k).any():
                centroids[k] = pts[labels == k].mean(0)
    history.append((labels.copy(), centroids.copy()))
    return labels, history


def layout(rng: np.random.Generator) -> np.ndarray:
    """Scatter skill points in plot space, mixed across true groups so kmeans
    has real work to do (positions ~ uniform-ish blobs with overlap)."""
    plot_w, plot_h = WIDTH - 2 * PAD, H - 140
    pts = []
    for k in range(K):
        # true center per group, but heavily overlapping + jittered
        cx = plot_w * (0.22 + 0.30 * k) + rng.normal(0, 40)
        cy = plot_h * rng.uniform(0.3, 0.7) + 110 + rng.normal(0, 25)
        n = len(CLUSTERS[k][2])
        pts.append(np.column_stack([
            np.clip(rng.normal(cx, 95, n), 20, plot_w - 20),
            np.clip(rng.normal(cy, 60, n), 120, plot_h + 60),
        ]))
    return np.vstack(pts)


def _anim(attr, vals, times, dur=LOOP, extra=""):
    inc = [min(1.0, max(0.0, t)) for t in times]
    for i in range(1, len(inc)):
        inc[i] = max(inc[i], inc[i - 1] + 1e-5)
    return (f'<animate attributeName="{attr}" values="{";".join(vals)}"'
            f' keyTimes="{";".join(f"{t:.4f}" for t in inc)}" dur="{dur}s"'
            f' repeatCount="indefinite"{extra}/>')


def build() -> str:
    seed = seed_today(salt=3)
    rng = np.random.default_rng(seed)
    pts = layout(rng)
    labels, hist = kmeans(pts, rng)
    n_it = len(hist) - 1

    # timeline: [0.06 cold] then n_it+1 segments of ITER_DUR, then settle+labels
    seg = ITER_DUR / LOOP
    t_cold = 0.05
    bounds = [t_cold + i * seg for i in range(n_it + 2)]

    svg = Svg(WIDTH, H, title="skills clustered by real k-means")
    frame(svg, grid=48)
    blueprint_label(svg, 28, 30, "01 — SKILLS × K-MEANS")
    svg.el(svg.text(WIDTH - 28, 30, f"{len(pts)} points · k={K} · {n_it} iterations",
                    10, FAINT, anchor="end", spacing=1))

    names = [n for _, _, lst in CLUSTERS for n in lst]

    # ---- greedy label placement: no two labels may overlap ---------------
    placed: list[tuple] = []            # occupied bboxes (x1, y1, x2, y2)

    def fits(bb):
        return all(bb[0] >= o[2] or bb[2] <= o[0] or bb[1] >= o[3] or bb[3] <= o[1]
                   for o in placed)

    # ---- points: circle + collision-free label, recolour per iteration -----
    for i, (x, y) in enumerate(pts):
        cols = [GONE]
        for lab_hist, _ in hist:
            lab = lab_hist[i]
            cols.append(CLUSTERS[lab][1] if lab >= 0 else GONE)
        times = [0.0] + bounds
        vals = [cols[min(j, len(cols) - 1)] for j in range(len(times))]
        vals[-1] = vals[-2]  # hold final
        circ = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{GONE}"'
                f' stroke="#000" stroke-width="0.5">'
                + _anim("fill", vals, times) + "</circle>")
        lbl = names[i]
        w_est = len(lbl) * 6.4 + 6      # generous estimate for 9.5px mono
        # try candidate anchors around the point until collision-free
        cands = [(x + 7, y + 3), (x - w_est - 3, y + 3), (x - w_est / 2, y - 10),
                 (x - w_est / 2, y + 16), (x + 7, y - 10), (x + 7, y + 16),
                 (x - w_est - 3, y - 10), (x - w_est - 3, y + 16),
                 (x - w_est / 2, y - 21), (x - w_est / 2, y + 27)]
        for lx, ly in cands:
            bb = (lx, ly - 9, lx + w_est, ly + 3)
            if 4 < bb[0] and bb[2] < WIDTH - 10 and 56 < bb[1] and bb[3] < H - 36 \
                    and fits(bb):
                placed.append(bb)
                txt = svg.text(lx, ly, lbl, 9.5, "#6A6A7A")
                break
        else:
            txt = ""                     # nowhere free — skip rather than collide
        svg.el(circ + txt)

    # ---- centroids: glide between iteration positions -----------------
    for k in range(K):
        pos = [h[1][k] for h in hist]
        xs = [p[0] for p in pos]
        ys = [p[1] for p in pos]
        times = [0.0] + bounds
        vx = [f"{xs[0]:.1f}"] + [f"{xs[min(j, len(xs) - 1)]:.1f}" for j in range(1, len(times))]
        vy = [f"{ys[0]:.1f}"] + [f"{ys[min(j, len(ys) - 1)]:.1f}" for j in range(1, len(times))]
        col = CLUSTERS[k][1]
        cx_el = (f'<path d="M -7 0 H 7 M 0 -7 V 7" stroke="{col}" stroke-width="2.4"'
                 f' fill="none" transform="translate({vx[1]} {vy[1]})" opacity="0.95">'
                 + '<animateTransform attributeName="transform" type="translate"'
                   f' values="{";".join(f"{a} {b}" for a, b in zip(vx, vy))}"'
                   f' keyTimes="{";".join(f"{t:.4f}" for t in times)}" dur="{LOOP}s"'
                   ' calcMode="spline" keySplines="' + "0.4 0 0.2 1;" * (len(times) - 1) + '"'
                   ' repeatCount="indefinite"/></path>')
        svg.el(cx_el)

    # ---- labels + hull circles appear at the end, fade on loop restart --
    final_centroids = hist[-1][1]
    appear = bounds[-1] - 0.25
    op_vals = ["0"] * len(bounds) + ["0", "1", "1", "0"]
    op_times = [0.0] + bounds + [bounds[-1] + 0.01, appear, 0.97, 1.0]
    for k, (name, col, lst) in enumerate(CLUSTERS):
        x, y = final_centroids[k]
        # clamp horizontally so centered labels never leave the canvas
        x = max(120.0, min(WIDTH - 120.0, x))
        grp = (
            svg.text(x, y - 42, f"◤ {name}", 13, col, anchor="middle", weight="bold",
                     spacing=2)
            + svg.text(x, y - 27, " · ".join(lst[:4]), 9, MUTED, anchor="middle")
        )
        svg.el(f'<g opacity="0">' + _anim("opacity", op_vals, op_times) + grp + "</g>")

    caption(svg, "// k-means++-ish init · lloyd iterations recorded in numpy · replayed as SMIL")
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "skills-kmeans.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
