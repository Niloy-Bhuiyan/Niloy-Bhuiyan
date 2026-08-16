"""Build the contribution calendar: GitHub's chrome, our palette, an amber snake.

Renders the real last-12-months grid with the count heading, month and weekday
labels, the Less/More legend and a per-year totals line -- then runs a snake
along a serpentine sweep, eating cells as it passes and regrowing them at the
end of each loop.
"""
import datetime as dt
import io
import os

import contrib
from theme import AMBER, BG, BORDER, MONO, MUTED, TEXT, esc

CELL, GAP = 11, 3
PITCH = CELL + GAP
COLS, ROWS = 53, 7

OX, OY = 46, 74                 # grid origin
W = OX + COLS * PITCH + 14
H = OY + ROWS * PITCH + 52

EMPTY = "#1c1c21"
LEVELS = [EMPTY, "#0e4429", "#006d32", "#26a641", "#39d353"]

LOOP = 21.0                     # seconds per full sweep
EAT_END = 0.86                  # fraction of the loop spent sweeping
SNAKE_LEN = 4

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def layout(days):
    """-> {(col,row): (level,count,date)}, first_date"""
    first = dt.date.fromisoformat(days[0][0])
    first -= dt.timedelta(days=(first.weekday() + 1) % 7)   # back up to Sunday
    grid = {}
    for iso, level, count in days:
        d = dt.date.fromisoformat(iso)
        col = (d - first).days // 7
        row = (d.weekday() + 1) % 7
        if 0 <= col < COLS:
            grid[(col, row)] = (level, count, d)
    return grid, first


def month_labels(first):
    out, seen = [], None
    for col in range(COLS):
        d = first + dt.timedelta(days=col * 7)
        if d.month != seen and col < COLS - 1:
            # only label once the month actually owns most of the column
            if d.day <= 7 or seen is None:
                out.append((col, MONTHS[d.month - 1]))
                seen = d.month
    return out


def sweep_order():
    """Serpentine path: left to right, drop a row, right to left."""
    path = []
    for row in range(ROWS):
        cols = range(COLS) if row % 2 == 0 else range(COLS - 1, -1, -1)
        path.extend((c, row) for c in cols)
    return path


def build():
    days = contrib.last_year()
    total = sum(c for _, _, c in days)
    grid, first = layout(days)
    totals = contrib.year_totals()

    path = sweep_order()
    steps = len(path)
    at = {cell: i for i, cell in enumerate(path)}

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{total} contributions in the last year">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<g font-family="{MONO}">',
        f'<text x="{OX}" y="34" font-size="15" fill="{TEXT}">{total} contributions '
        f'<tspan fill="{MUTED}">in the last year</tspan></text>',
    ]

    # month labels
    for col, name in month_labels(first):
        out.append(
            f'<text x="{OX + col * PITCH}" y="{OY - 10}" font-size="10" fill="{MUTED}">{name}</text>'
        )

    # weekday labels
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = OY + row * PITCH + CELL - 1.5
        out.append(
            f'<text x="{OX - 9}" y="{y}" font-size="9.5" fill="{MUTED}" text-anchor="end">{name}</text>'
        )

    # cells
    for (col, row), (level, count, d) in sorted(grid.items()):
        x, y = OX + col * PITCH, OY + row * PITCH
        base = LEVELS[level]
        s = at[(col, row)] / steps
        t_eat = EAT_END * s
        k = [0.0, t_eat, min(t_eat + 0.006, 1.0), 0.90 + 0.075 * s]
        k.append(min(k[3] + 0.015, 0.999))
        k.append(1.0)
        vals = f"{base};{base};{EMPTY};{EMPTY};{base};{base}"
        keys = ";".join(f"{v:.4f}" for v in k)
        label = f"{count} contribution{'' if count == 1 else 's'} on {d:%b} {d.day}, {d.year}"
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{base}">'
            f'<title>{esc(label)}</title>'
            + (
                f'<animate attributeName="fill" values="{vals}" keyTimes="{keys}" '
                f'dur="{LOOP}s" repeatCount="indefinite"/>'
                if level > 0 else ""
            )
            + "</rect>"
        )

    # snake -- head plus a short tail, each segment trailing by one step
    pts = [(OX + c * PITCH, OY + r * PITCH) for c, r in path]
    keytimes = ";".join(f"{EAT_END * i / (steps - 1):.5f}" for i in range(steps)) + ";1"

    for seg in range(SNAKE_LEN, -1, -1):
        rot = pts[-seg:] + pts[:-seg] if seg else pts
        vals = ";".join(f"{x},{y}" for x, y in rot) + f";{rot[-1][0]},{rot[-1][1]}"
        # full-cell segments so the body reads as one snake, not a row of dots
        inset = -1 if seg == 0 else 0
        size = CELL - 2 * inset
        op = 1.0 if seg == 0 else max(0.3, 0.82 - (seg - 1) * 0.17)
        out.append(
            f'<g><rect x="{inset}" y="{inset}" width="{size:.1f}" height="{size:.1f}" '
            f'rx="3" fill="{AMBER}" opacity="{op:.2f}"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{vals}" keyTimes="{keytimes}" dur="{LOOP}s" '
            f'calcMode="linear" repeatCount="indefinite"/></g>'
        )

    # legend + per-year totals
    ly = OY + ROWS * PITCH + 26
    out.append(f'<text x="{OX}" y="{ly}" font-size="10.5" fill="{MUTED}">'
               + "".join(
                   f'<tspan fill="{TEXT}">{y}</tspan>'
                   f'<tspan fill="{MUTED}"> · {t}{"    " if i < len(totals) - 1 else ""}</tspan>'
                   for i, (y, t) in enumerate(totals)
               )
               + "</text>")

    lx = W - 14 - 5 * (CELL + 2) - 62
    out.append(f'<text x="{lx}" y="{ly}" font-size="10" fill="{MUTED}">Less</text>')
    for i, c in enumerate(LEVELS):
        out.append(
            f'<rect x="{lx + 26 + i * (CELL + 2)}" y="{ly - 9}" width="{CELL}" height="{CELL}" '
            f'rx="2" fill="{c}"/>'
        )
    out.append(f'<text x="{lx + 26 + 5 * (CELL + 2) + 4}" y="{ly}" font-size="10" '
               f'fill="{MUTED}">More</text>')

    out.append("</g></svg>")
    return "".join(out)


if __name__ == "__main__":
    import sys

    dest = sys.argv[1] if len(sys.argv) > 1 else "assets/contributions.svg"
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    svg = build()
    with io.open(dest, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", dest, len(svg), "bytes")
