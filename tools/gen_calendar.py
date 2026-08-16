"""Build the contribution calendar: GitHub's chrome, our palette, an amber snake.

Renders the real last-12-months grid with the count heading, month and weekday
labels, the Less/More legend and a per-year totals line -- then runs a snake
that hunts the cells with contributions, eating them as it reaches them and
regrowing the grid at the end of each loop.
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


def _walk(a, b, horiz_first):
    """Unit steps from a to b along an L, excluding a and including b."""
    (x0, y0), (x1, y1) = a, b
    out = []
    if horiz_first:
        legs = ((x0, x1, "x"), (y0, y1, "y"))
    else:
        legs = ((y0, y1, "y"), (x0, x1, "x"))
    x, y = x0, y0
    for start, end, axis in legs:
        step = 1 if end >= start else -1
        for v in range(start + step, end + step, step):
            if axis == "x":
                x = v
            else:
                y = v
            out.append((x, y))
    return out


def snake_path(grid):
    """A route that hunts the cells with contributions instead of mowing rows.

    Nearest neighbour over the non-empty cells, joined by L-shaped moves that
    alternate which axis leads, so the snake turns rather than sweeping. The
    tour closes back on its start point so the loop is seamless.
    """
    targets = sorted(c for c, (level, _, _) in grid.items() if level > 0)
    start = (0, 3)
    if not targets:
        return [start]

    remaining, tour, cur = set(targets), [start], start
    while remaining:
        nxt = min(remaining, key=lambda c: (abs(c[0] - cur[0]) + abs(c[1] - cur[1]), c))
        tour.append(nxt)
        remaining.discard(nxt)
        cur = nxt
    tour.append(start)

    path = [start]
    for i in range(1, len(tour)):
        path.extend(_walk(tour[i - 1], tour[i], horiz_first=(i % 2 == 1)))
    return path


def build():
    days = contrib.last_year()
    total = sum(c for _, _, c in days)
    grid, first = layout(days)
    totals = contrib.year_totals()

    path = snake_path(grid)
    cycle = path[:-1] if len(path) > 1 and path[-1] == path[0] else path
    steps = len(cycle)

    at = {}                                   # first moment the snake covers a cell
    for i, cell in enumerate(cycle):
        at.setdefault(cell, i)

    loop = min(30.0, max(13.0, steps * 0.07))

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
        visit = at.get((col, row))
        s = (visit / steps) if visit is not None else None
        if s is not None:
            t_eat = EAT_END * s
            k = [0.0, t_eat, min(t_eat + 0.006, 1.0), EAT_END + 0.03 + 0.045 * s]
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
                f'dur="{loop}s" repeatCount="indefinite"/>'
                if level > 0 and s is not None else ""
            )
            + "</rect>"
        )

    # snake -- head plus a short tail, each segment trailing by one step
    pts = [(OX + c * PITCH, OY + r * PITCH) for c, r in cycle]
    # one key per position around the closed tour, then a hold while cells regrow
    keytimes = ";".join(f"{EAT_END * i / steps:.5f}" for i in range(steps + 1)) + ";1"

    for seg in range(SNAKE_LEN, -1, -1):
        rot = pts[-seg:] + pts[:-seg] if seg else pts
        closed = rot + [rot[0], rot[0]]
        vals = ";".join(f"{x},{y}" for x, y in closed)
        # full-cell segments so the body reads as one snake, not a row of dots
        inset = -1 if seg == 0 else 0
        size = CELL - 2 * inset
        op = 1.0 if seg == 0 else max(0.3, 0.82 - (seg - 1) * 0.17)
        out.append(
            f'<g><rect x="{inset}" y="{inset}" width="{size:.1f}" height="{size:.1f}" '
            f'rx="3" fill="{AMBER}" opacity="{op:.2f}"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{vals}" keyTimes="{keytimes}" dur="{loop}s" '
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
