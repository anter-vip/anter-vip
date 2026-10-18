"""
sorting_visualizer.py — runs a REAL QuickSort (Lomuto partition) on random
bars, records the array state after every swap AND which slot was the pivot,
then replays it as discrete SMIL keyframes: bars jump to their new x slots,
the active pivot glows violet, freshly-swapped bars flash cyan.

Frame count is hard-capped at MAX_STATES swaps so the SVG stays light; if the
random instance needs more, the replay simply shows the first MAX_STATES steps
(the caption reports which happened).
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    CYAN, VIOLET, FAINT, LINE, WIDTH,
    Svg, frame, blueprint_label, caption, seed_today,
)

H = 360
N_BARS = 26
MAX_STATES = 140
LOOP = 13.0
PLOT_X, = (35,)
BASE_Y = H - 78
BAR_W, GAP = 22, 8
REST = "#162A31"      # resting bar fill (dark cyan-slate)
COLD = "#16161E"      # before the sort starts


def quicksort_identity(heights: list[int]):
    """Lomuto quicksort on (id, value) pairs. Returns
    states[i] = list of (id, value) after i swaps, pivots[i] = pivot SLOT
    during state i, swapped_ids[i] = set of bar ids moved into/out of slots
    by the swap that produced state i."""
    arr = list(enumerate(heights))
    states, pivots, swapped = [list(arr)], [-1], [set()]

    def emit(pivot_slot, moved_ids):
        if len(states) > MAX_STATES:
            return False
        states.append(list(arr))
        pivots.append(pivot_slot)
        swapped.append(set(moved_ids))
        return True

    def partition(lo, hi):
        p = arr[hi][1]
        i = lo - 1
        for j in range(lo, hi):
            if len(states) > MAX_STATES:
                return hi
            if arr[j][1] <= p:
                i += 1
                if i != j:
                    arr[i], arr[j] = arr[j], arr[i]
                    emit(hi, {arr[i][0], arr[j][0]})
        i += 1
        if i != hi:
            arr[i], arr[hi] = arr[hi], arr[i]
            emit(i, {arr[i][0], arr[hi][0]})
        else:
            emit(i, set())
        return i

    def qs(lo, hi):
        if len(states) > MAX_STATES or lo >= hi:
            return
        pi = partition(lo, hi)
        qs(lo, pi - 1)
        qs(pi + 1, hi)

    qs(0, len(arr) - 1)
    return states, pivots, swapped


def build() -> str:
    seed = seed_today(salt=4)
    rng = np.random.default_rng(seed)
    heights = rng.integers(28, 205, N_BARS).tolist()   # unique enough, mostly distinct
    states, pivots, swapped = quicksort_identity(heights)
    n = len(states)
    capped = n > MAX_STATES
    final_vals = [v for _, v in states[-1]]

    # timeline: cold hold, then one discrete step per state, then hold + snap back
    cold = 0.9 / LOOP
    st = (LOOP * 0.80) / n
    times = ([0.0] + [min(0.993, cold + (i + 1) * st / LOOP) for i in range(n)]
             + [0.9965, 1.0])
    ts_attr = ";".join(f"{t:.4f}" for t in times)

    svg = Svg(WIDTH, H, title="quicksort visualizer")
    frame(svg, grid=48)
    blueprint_label(svg, 28, 30, "SORTING ALGORITHM")
    svg.el(svg.text(WIDTH - 28, 30,
                    f"quicksort · lomuto · {n - 1} recorded swaps · "
                    + ("frame-capped" if capped else "sorted ✓"),
                    10, FAINT, anchor="end", spacing=1))

    slot_x = lambda s: PLOT_X + s * (BAR_W + GAP)  # noqa: E731
    baseline_y = BASE_Y + 8
    svg.el(f'<line x1="{PLOT_X - 12}" y1="{baseline_y}"'
           f' x2="{slot_x(N_BARS) - GAP + 12}" y2="{baseline_y}" stroke="{LINE}"/>')

    for v_i, h0 in enumerate(heights):
        # position of THIS bar (by identity) in every recorded state
        xs = [next(k for k, (idn, _) in enumerate(stt) if idn == v_i) for stt in states]
        val_x = ";".join(
            [f"{slot_x(xs[0]):.1f}"] + [f"{slot_x(p):.1f}" for p in xs]
            + [f"{slot_x(xs[-1]):.1f}", f"{slot_x(xs[0]):.1f}"]
        )
        # fill per state: violet if this bar sits on the active pivot slot,
        # cyan if the transition INTO this state moved it, else resting
        fills = [COLD]
        for s in range(n):
            if s == 0:
                fills.append(COLD)                    # initial unsorted state
            elif v_i in swapped[s]:
                fills.append(CYAN)
            elif xs[s] == pivots[s] and pivots[s] >= 0:
                fills.append(VIOLET)
            else:
                fills.append(REST)
        fills += [fills[-1], COLD]        # hold, then snap back for the loop
        val_f = ";".join(fills)

        svg.el(
            f'<rect x="{slot_x(xs[0]):.1f}" y="{BASE_Y - h0}" width="{BAR_W}"'
            f' height="{h0}" rx="3" fill="{COLD}" stroke="{LINE}" stroke-width="0.6">'
            f'<animate attributeName="x" values="{val_x}" keyTimes="{ts_attr}"'
            f' calcMode="discrete" dur="{LOOP}s" repeatCount="indefinite"/>'
            f'<animate attributeName="fill" values="{val_f}" keyTimes="{ts_attr}"'
            f' calcMode="discrete" dur="{LOOP}s" repeatCount="indefinite"/>'
            f"</rect>"
        )

    caption(svg, "// I like my data sorted. — every frame is a real recorded swap")
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "sorting.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
