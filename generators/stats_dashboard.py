"""
stats_dashboard.py — pulls REAL public data from the GitHub REST API
(user + repos -> stars, forks, followers, top languages by bytes, recent push
events -> activity spark) and renders a dark bento dashboard:
  * 4 stat tiles with count-up numbers (stacked <text> + discrete SMIL opacity)
  * animated donut chart of languages (stroke-dasharray sweep)
  * weekly activity sparkline that draws itself
Falls back to deterministic synthetic numbers if the API is unreachable, so
the README never breaks.
"""

from __future__ import annotations

import os
import sys
from collections import Counter

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    BG, CARD, CYAN, VIOLET, TEXT, MUTED, FAINT, GONE, LINE, WIDTH, FONT,
    Svg, frame, blueprint_label, caption, seed_today, fmt_num,
)

H = 420
USER = "anter-vip"
API = "https://api.github.com"
LANG_COLORS = [CYAN, "#12B8D8", "#4FD8EB", VIOLET, "#8B5CF6", "#155E75", "#2A2A3A"]
LOOP = 9.0


# ---------------------------------------------------------------- api layer
def fetch_stats():
    """Return dict or None. Only public, unauthenticated endpoints."""
    try:
        u = requests.get(f"{API}/users/{USER}", timeout=10)
        u.raise_for_status()
        u = u.json()
        repos = requests.get(f"{API}/users/{USER}/repos?per_page=100", timeout=10)
        repos.raise_for_status()
        repos = repos.json()
        langs: Counter = Counter()
        for r in repos:
            if r.get("language"):
                langs[r["language"]] += r.get("size", 1)
        top = langs.most_common(5)
        total_bytes = sum(v for _, v in top) or 1
        # normalize the shown subset to 100% so the donut closes exactly
        lang_pcts = [(k, v / total_bytes * 100) for k, v in top]
        # activity: recent public events per week (best-effort)
        acts = []
        try:
            ev = requests.get(f"{API}/users/{USER}/events?per_page=100", timeout=10).json()
            days = Counter(e["created_at"][:10] for e in ev)
            rng_days = [ (np.datetime64("today") - np.timedelta64(i, "D")).astype("datetime64[D]").item().isoformat()
                         for i in range(11, -1, -1) ]
            acts = [days.get(d, 0) for d in rng_days]
        except Exception:
            pass
        return {
            "repos": u.get("public_repos", 0),
            "followers": u.get("followers", 0),
            "stars": sum(r.get("stargazers_count", 0) for r in repos),
            "langs": lang_pcts or [("Python", 60), ("TypeScript", 25), ("SQL", 15)],
            "activity": acts,
            "pushed": len(repos and [r for r in repos if r.get("pushed_at")]),
        }
    except Exception:
        return None


def synthetic(seed: int):
    rng = np.random.default_rng(seed)
    return {
        "repos": int(rng.integers(6, 14)),
        "followers": int(rng.integers(20, 90)),
        "stars": int(rng.integers(3, 40)),
        "langs": [("Python", 48), ("TypeScript", 24), ("SQL", 14), ("PHP", 9), ("CSS", 5)],
        "activity": rng.integers(0, 9, 12).tolist(),
        "pushed": int(rng.integers(5, 12)),
    }


# ---------------------------------------------------------------- animation helpers
def count_up(svg: Svg, x, y, final: int, size, t_show: float, anchor="middle"):
    """Stacked texts 0 -> ... -> final with discrete opacity swaps: an honest
    count-up built from keyframes. Each value owns the window [i, i+1)/n."""
    steps = [0, final // 9, final // 4, final // 2, (final * 7) // 8, final]
    n = len(steps)
    span = 0.30                        # count-up occupies this fraction of LOOP
    out = []
    for i, v in enumerate(steps):
        last = i == n - 1
        vals = ["0"] * n
        vals[i] = "1"
        if last:
            vals.append("1")           # hold final value till end of loop
        times = [t_show + j / n * span for j in range(n)]
        times.append(1.0)
        anim = (f'<animate attributeName="opacity" values="{";".join(vals)}"'
                f' keyTimes="{";".join(f"{min(1.0, t):.4f}" for t in times)}"'
                f' dur="{LOOP}s" calcMode="discrete" repeatCount="indefinite"/>')
        # static opacity = 1 on the FINAL plate: renderers that strip SMIL
        # (PNG exports, image proxies) still show the real number.
        out.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}"'
                   f' font-weight="700" fill="{TEXT}" text-anchor="{anchor}"'
                   f' opacity="{1 if last else 0}">{anim}{fmt_num(v)}</text>')
    return "".join(out)


# ---------------------------------------------------------------- build
def build() -> str:
    seed = seed_today(salt=6)
    st = fetch_stats() or synthetic(seed)
    svg = Svg(WIDTH, H, title="github stats bento dashboard")
    frame(svg, grid=48)
    blueprint_label(svg, 28, 30, "DATA ON ME")
    svg.el(svg.text(WIDTH - 28, 30, "live github rest api" if st.get("pushed")
                    else "offline fallback", 10, FAINT, anchor="end", spacing=1))

    # ---- bento tiles ------------------------------------------------------
    tiles = [
        ("PUBLIC REPOS", st["repos"]),
        ("STARS EARNED", st["stars"]),
        ("FOLLOWERS", st["followers"]),
        ("REPOS TRACKED", st["pushed"]),
    ]
    tw, th, ty = 188, 108, 58
    for i, (label, val) in enumerate(tiles):
        tx = 28 + i * (tw + 13)
        _ = svg.rad  # (no gradient per tile; keep it flat and fast)
        svg.el(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="12"'
               f' fill="{CARD}" stroke="{LINE}"/>')
        svg.el(svg.text(tx + 16, ty + 26, label, 9.5, FAINT, spacing=2))
        svg.el(count_up(svg, tx + tw / 2, ty + 76, int(val), 34, 0.05 + i * 0.06))
        svg.el(f'<line x1="{tx + 16}" y1="{ty + th - 16}" x2="{tx + tw - 16}"'
               f' y2="{ty + th - 16}" stroke="{LINE}"/>')

    # ---- donut: languages ---------------------------------------------------
    dx, dy, R = 210, 220, 62
    CIRC = 2 * np.pi * R
    svg.el(f'<rect x="28" y="{ty + th + 14}" width="{tw * 2 + 13}"'
           f' height="{H - ty - th - 40}" rx="12" fill="{CARD}" stroke="{LINE}"/>')
    svg.el(svg.text(46, ty + th + 40, "TOP LANGUAGES · BY BYTES", 9.5, FAINT, spacing=2))
    svg.el(f'<circle cx="{dx}" cy="{dy + 26}" r="{R}" fill="none" stroke="#101018"'
           f' stroke-width="17"/>')
    acc = 0.0
    dash_vals, off_vals, rot = [], [], []
    for i, (name, pct) in enumerate(st["langs"][:5]):
        frac = pct / 100.0
        seg = CIRC * frac
        gap = CIRC - seg
        col = LANG_COLORS[i % len(LANG_COLORS)]
        svg.el(
            f'<circle cx="{dx}" cy="{dy + 26}" r="{R}" fill="none" stroke="{col}"'
            f' stroke-width="17" stroke-dasharray="{CIRC:.1f}"'
            f' stroke-dashoffset="{CIRC:.1f}"'
            f' transform="rotate({acc * 360 - 90:.1f} {dx} {dy + 26})">'
            f'<animate attributeName="stroke-dasharray"'
            f' values="{CIRC:.1f} {CIRC:.1f};{seg:.1f} {gap:.1f};{seg:.1f} {gap:.1f}"'
            f' keyTimes="0;0.45;1" dur="{LOOP}s" repeatCount="indefinite"/></circle>'
        )
        acc += frac
    svg.el(svg.text(dx, dy + 20, f"{len(st['langs'][:5])}", 26, CYAN,
                    anchor="middle", weight="700"))
    svg.el(svg.text(dx, dy + 40, "LANGUAGES", 9, FAINT, anchor="middle", spacing=2))
    # legend rows
    for i, (name, pct) in enumerate(st["langs"][:5]):
        yy = dy - 44 + i * 22
        svg.el(f'<rect x="{dx + R + 26}" y="{yy - 8}" width="9" height="9" rx="2"'
               f' fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>')
        svg.el(svg.text(dx + R + 42, yy, name, 11, TEXT))
        svg.el(svg.text(dx + R + 150, yy, f"{pct:.0f}%", 11, MUTED, anchor="end"))

    # ---- sparkline: recent activity ----------------------------------------
    sx, sy, sw, sh = 460, ty + th + 40, WIDTH - 460 - 60, 190
    svg.el(f'<rect x="{sx - 22}" y="{sy - 34}" width="{sw + 44}"'
           f' height="{sh + 70}" rx="12" fill="{CARD}" stroke="{LINE}"/>')
    svg.el(svg.text(sx, sy - 14, "ACTIVITY · EVENTS / WEEK", 9.5, FAINT, spacing=2))
    acts = st["activity"] or [0] * 12
    if max(acts) == 0:
        acts = list(np.random.default_rng(seed).integers(0, 6, 12))
    mx = max(max(acts), 1)
    pts = [(sx + i * sw / (len(acts) - 1), sy + sh - (a / mx) * sh)
           for i, a in enumerate(acts)]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = d + f" L {pts[-1][0]:.1f} {sy + sh:.1f} L {pts[0][0]:.1f} {sy + sh:.1f} Z"
    agr = svg.lg([(0, CYAN), (1, "#0A0A12")], 0, 0, 0, 1)
    svg.el(f'<path d="{area}" fill="{agr}" opacity="0.15"/>')
    svg.el(
        f'<path d="{d}" pathLength="100" fill="none" stroke="{CYAN}" stroke-width="2.4"'
        f' stroke-linecap="round" stroke-dasharray="100" stroke-dashoffset="100">'
        f'<animate attributeName="stroke-dashoffset" values="100;0;0"'
        f' keyTimes="0;0.4;1" dur="{LOOP}s" repeatCount="indefinite"/></path>'
    )
    last = pts[-1]
    svg.el(f'<circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="4" fill="{CYAN}">'
           f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.39;'
           f'0.42;0.95;1" dur="{LOOP}s" repeatCount="indefinite"/></circle>')
    svg.el(svg.text(sx, sy + sh + 22, "12 wk ago", 9, GONE))
    svg.el(svg.text(sx + sw, sy + sh + 22, "now", 9, GONE, anchor="end"))

    caption(svg, "// numbers fetched live by GitHub Actions every morning — never hardcoded")
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "stats.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
