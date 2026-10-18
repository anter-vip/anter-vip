"""
life_contributions.py — fetches the REAL contribution calendar via GitHub
GraphQL (needs GITHUB_TOKEN, provided automatically in Actions), seeds
Conway's Game of Life with it, simulates ~44 generations in numpy and animates
the grid evolving generation by generation (discrete SMIL opacity per frame —
one <g> per generation keeps the file tiny).

Graceful degradation: no token / API down -> a deterministic synthetic
calendar seeded by the date, so the README NEVER breaks.
"""

from __future__ import annotations

import datetime
import os
import sys

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    CYAN, CYAN_DIM, FAINT, GONE, LINE, MUTED, WIDTH,
    Svg, frame, blueprint_label, caption, seed_today,
)

H = 380
WEEKS = 27                  # columns (last ~6 months fit the 850px canvas)
CELL, GAP = 12, 2           # cell pitch
GENS = 44
GEN_SEC = 0.26
API = "https://api.github.com/graphql"

LEVEL_COLORS = {0: GONE, 1: "#0C3540", 2: "#0A6C7A", 3: "#12B8D8", 4: CYAN}


def fetch_calendar():
    """Return list[list[int 0..4]] (weeks x days) or None."""
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        return None
    from_user = (datetime.date.today() - datetime.timedelta(days=WEEKS * 7 + 6)).isoformat()
    q = """
    query($from: DateTime!) {
      user(login: "anter-vip") {
        contributions {
          calendar(from: $from) {
            weeks { contributionDays { contributionLevel date } }
          }
        }
      }
    }"""
    lvl = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
           "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    try:
        r = requests.post(API, json={"query": q, "variables": {"from": from_user}},
                          headers={"Authorization": f"bearer {tok}"}, timeout=15)
        r.raise_for_status()
        weeks = r.json()["data"]["user"]["contributions"]["calendar"]["weeks"]
        grid = [[lvl.get(d["contributionLevel"], 0) for d in w["contributionDays"]]
                for w in weeks]
        # pad incomplete last week
        grid += [[0] * 7] * (WEEKS - len(grid)) if len(grid) < WEEKS else []
        return grid[:WEEKS]
    except Exception:
        return None


def synthetic_calendar(seed: int):
    rng = np.random.default_rng(seed)
    base = rng.random((WEEKS, 7))
    boost = 0.35 if rng.random() > 0.5 else 0.0          # weekday rhythm
    day_w = np.array([boost, 0.25, 0.22, 0.24, 0.2, 0.05, 0.0])
    lv = np.clip(base + np.tile(day_w, (WEEKS, 1)), 0, 1)
    return ((lv * 5).astype(int).clip(0, 4)).tolist()


def life_seed(grid):
    """Boolean board from contribution levels (>0 alive)."""
    return np.array([[1 if c > 0 else 0 for c in week] for week in grid], dtype=bool)


def step(board: np.ndarray) -> np.ndarray:
    """One Conway generation (no wrap, dead border)."""
    p = np.pad(board, 1)
    nb = (p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:] + p[1:-1, :-2] +
          p[1:-1, 2:] + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:])
    return (nb == 3) | (board & (nb == 2))


def build() -> str:
    seed = seed_today(salt=5)
    real = fetch_calendar()
    grid = real if real else synthetic_calendar(seed)
    src = "github graphql" if real else f"synthetic seed {seed}"

    board0 = life_seed(grid)
    gens = [board0]
    for _ in range(GENS - 1):
        gens.append(step(gens[-1]))

    n = len(gens[0])                       # columns actually used
    gw = n * (CELL + GAP)
    ox = (WIDTH - gw) / 2
    oy = 96

    svg = Svg(WIDTH, H, title="conway life seeded from contribution graph")
    frame(svg, grid=48)
    blueprint_label(svg, 28, 30, "CONTRIBUTIONS × GAME OF LIFE")
    svg.el(svg.text(WIDTH - 28, 30, f"source: {src} · {GENS} generations",
                    10, FAINT, anchor="end", spacing=1))

    # ---- static base: every cell in its true contribution color ----------
    base = []
    for c, week in enumerate(grid):
        for r, lv in enumerate(week):
            x, y = ox + c * (CELL + GAP), oy + r * (CELL + GAP)
            base.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{CELL}" height="{CELL}"'
                        f' rx="2.5" fill="{LEVEL_COLORS[lv]}"/>')
    svg.el("".join(base))

    # ---- evolution overlay: one <g> per generation, discrete blink -------
    total = GENS * GEN_SEC + 2.2
    times = [0.0] + [min(0.965, (i + 1) * GEN_SEC / total) for i in range(GENS)] \
            + [0.985, 1.0]
    ts = ";".join(f"{t:.4f}" for t in times)
    cells_alive = []
    for g in gens:
        idxs = np.argwhere(g)
        chunk = "".join(
            f'<rect x="{ox + c * (CELL + GAP):.0f}" y="{oy + (r % 7) * (CELL + GAP):.0f}"'
            f' width="{CELL}" height="{CELL}" rx="2.5" fill="{CYAN}" opacity="0.9"/>'
            for r, c in idxs
        )
        cells_alive.append(chunk)
    # each generation g is visible during its time slot only:
    # opacity values = 0..1..0 window per frame — but to keep it cheap we toggle
    # a single <set> sequence via discrete fill-opacity animation per group.
    overlays = []
    for gi, chunk in enumerate(cells_alive):
        # one value per keyTime (excluding final 1.0); visible only in slot gi
        vals = ["0"] * (len(times) - 1)
        vals[gi] = "1"
        anim = (f'<animate attributeName="opacity" values="{";".join(vals)}"'
                f' keyTimes="{";".join(f"{t:.4f}" for t in times[:-1])}"'
                f' dur="{total:.2f}s" calcMode="discrete" repeatCount="indefinite"/>')
        overlays.append(f"<g>{anim}{chunk}</g>")
    svg.el("".join(overlays))

    # ---- week ticks + legend ----------------------------------------------
    svg.el(f'<line x1="{ox:.0f}" y1="{oy - 14}" x2="{ox + gw:.0f}" y2="{oy - 14}"'
           f' stroke="{LINE}"/>')
    months = "J F M A M J J A S O N D".split()
    for c in range(0, n, 4):
        x = ox + c * (CELL + GAP)
        svg.el(svg.text(x, oy - 22, months[(c + seed % 12) % 12], 9, FAINT))
    lx = ox
    ly = oy + 7 * (CELL + GAP) + 30
    svg.el(svg.text(lx, ly, "less", 10, MUTED))
    for i, lv in enumerate(range(5)):
        x = lx + 44 + i * 18
        svg.el(f'<rect x="{x}" y="{ly - 9}" width="12" height="12" rx="2.5"'
               f' fill="{LEVEL_COLORS[lv]}"/>')
    svg.el(svg.text(x + 22, ly, "more", 10, MUTED))
    svg.el(svg.text(lx + 250, ly, f"alive cells gen 0 → {int(board0.sum())}"
                    f" · Conway rules replayed in numpy", 10, FAINT))

    caption(svg, "// your contribution graph is the initial state — then life takes over")
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "life.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
