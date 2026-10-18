"""
terminal_intro.py — a fake macOS terminal window whose lines "type out"
character by character. No JS: each line is wrapped in a clip-path rect whose
width advances in discrete SMIL steps (one step per character), and a block
cursor translates to the revealed edge with the same discrete timeline.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    BG, CARD, LINE, CYAN, CYAN_DIM, TEXT, MUTED, FAINT, GONE, WIDTH, FONT,
    Svg, frame, seed_today,
)

H = 330
CH = 8.4            # advance width of one monospace char at 14px
STEP = 0.055        # seconds per typed character
LOOP = 13.0         # full cycle incl. pause before replay

# (prompt, command, response) — response appears after a short think pause
LINES = [
    ("$", "whoami", "Ahmed Anter — Data Analyst · Software Developer"),
    ("$", "cat role.txt", "Python · SQL · Power BI · TypeScript · React"),
    ("$", "python insights.py --from raw_data", "Turning raw data into decisions."),
    ("$", "git log --oneline -1", "feat(anter-vip): profile regenerated daily by GH Actions"),
]


def _discrete(vals, times):
    """SMIL values/keyTimes helper with discrete stepping."""
    return (' values="{}" keyTimes="{}" calcMode="discrete"'
            .format(";".join(str(v) for v in vals),
                    ";".join(f"{t:.4f}" for t in times)))


def typed_line(svg: Svg, idx: int, x: float, y: float, prompt: str,
               cmd: str, resp: str, t0: float) -> float:
    """Emit one typing line; returns the time when it finished."""
    full = f"{prompt} {cmd}"
    n_cmd = len(full)
    n_resp = len(resp) + 1 if resp else 0
    chars = n_cmd + n_resp
    width_cmd = n_cmd * CH
    width_all = chars * CH

    # prompt (cyan $) + command + response texts, clipped by an advancing rect
    clip_id = f"tc{idx}"
    anim = _discrete(
        [0] * 2 + [i * CH for i in range(1, chars + 1)] * 2,
        _times(chars, t0),
    )
    svg.defs(
        f'<clipPath id="{clip_id}"><rect x="{x:.1f}" y="{y - 16:.1f}" width="0" height="22">'
        f'<animate attributeName="width"{anim}/>'
        f"</rect></clipPath>"
    )
    texts = svg.text(x, y, "$", 14, CYAN, weight="bold")
    texts += svg.text(x + CH, y, full[2:], 14, TEXT)
    if resp:
        texts += svg.text(x + width_cmd + CH, y, resp, 14, MUTED)
    svg.el(f'<g clip-path="url(#{clip_id})">{texts}</g>')
    return t0 + chars * STEP + 0.35


def _times(chars: int, t0: float):
    """keyTimes for a discrete typing reveal that then HOLDS until LOOP end."""
    ts = [0.0, t0 / LOOP]
    for i in range(chars + 1):
        ts.append(min(1.0, (t0 + (i + 1) * STEP) / LOOP))
    ts.append(1.0)
    # clamp strictly increasing
    for i in range(1, len(ts)):
        ts[i] = max(ts[i], ts[i - 1] + 1e-5)
    return ts[: len(ts)]


def build() -> str:
    seed = seed_today(salt=2)
    svg = Svg(WIDTH, H, title="terminal intro")
    frame(svg, grid=48)

    # window
    wx, wy, ww, wh = 55, 40, WIDTH - 110, H - 88
    svg.el(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="12"'
           f' fill="{CARD}" stroke="{LINE}"/>')
    svg.el(f'<rect x="{wx}" y="{wy}" width="{ww}" height="34" rx="12" fill="#101018"/>')
    svg.el(f'<line x1="{wx}" y1="{wy + 34}" x2="{wx + ww}" y2="{wy + 34}"'
           f' stroke="{LINE}"/>')
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        svg.el(f'<circle cx="{wx + 24 + i * 20}" cy="{wy + 17}" r="6" fill="{c}"/>')
    svg.el(svg.text(wx + ww / 2, wy + 21, "anter@datastream — zsh", 11, FAINT,
                    anchor="middle", spacing=1))
    svg.el(svg.text(wx + ww - 14, wy + 21, f"session #{seed}", 10, GONE,
                    anchor="end"))

    # typing lines, sequential
    t = 0.8
    x0 = wx + 26
    for idx, (p, cmd, resp) in enumerate(LINES):
        y = wy + 66 + idx * 46
        t = typed_line(svg, idx, x0, y, p, cmd, resp, t)

    # block cursor parked after the last line, blinking (not typed — it idles)
    last_y = wy + 66 + (len(LINES) - 1) * 46
    cx = x0 + (len(f"$ {LINES[-1][1]}") + len(LINES[-1][2]) + 1) * CH
    svg.el(
        f'<rect x="{cx:.1f}" y="{last_y - 13}" width="8" height="16" fill="{CYAN}">'
        f'<animate attributeName="fill-opacity" values="1;0" dur="1s"'
        f' repeatCount="indefinite" calcMode="discrete"/></rect>'
    )
    # faint echoed chars decoration bottom-right
    svg.el(svg.text(wx + ww - 14, wy + wh - 12, "⌥⌘◊ ⎋ ⌫ ⏎", 12, GONE, anchor="end"))
    return svg.tostring()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets", "terminal.svg")
    with open(out, "w") as f:
        f.write(build())
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.1f} KB)")
