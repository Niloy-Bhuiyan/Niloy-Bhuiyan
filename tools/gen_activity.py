"""Build the monthly activity chart.

Replaces github-readme-activity-graph, which now answers 402 (the hosted service
ran out of quota) and rendered as a broken image on the profile. Same idea, our
own palette, and the numbers come from the same public contribution endpoint the
calendar uses -- so the two visuals can never disagree.
"""
import datetime as dt
import io
import os

import contrib
from theme import AMBER, BG, BORDER, MONO, MUTED, TEXT, esc

W, H = 900, 240
L, R = 52, 30                   # plot margins
TOP, BOT = 62, 46
PW = W - L - R
PH = H - TOP - BOT

GREEN = "#39d353"
AREA = "#26a641"
GRID = "#1e1e24"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly(days):
    """-> [(date-of-first-of-month, total)] for the 12 months the grid covers."""
    buckets = {}
    for iso, _, count in days:
        d = dt.date.fromisoformat(iso)
        buckets[(d.year, d.month)] = buckets.get((d.year, d.month), 0) + count
    keys = sorted(buckets)[-12:]
    return [(dt.date(y, m, 1), buckets[(y, m)]) for y, m in keys]


def nice_ceiling(v):
    """Round the axis top up to something a person would have chosen."""
    if v <= 5:
        return 5
    for step in (5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if v <= step * 4:
            return -(-v // step) * step
    return -(-v // 1000) * 1000


def spline(pts, tension=0.5):
    """Catmull-Rom through every point, emitted as cubic beziers.

    The hosted graph this replaces drew a smooth curve, so this one does too.
    Control points are clamped to the plot band: a Catmull-Rom that overshoots
    would dip the curve below zero after a quiet month, which would be a lie.
    """
    if len(pts) < 2:
        return "M" + ",".join(f"{v:.1f}" for v in pts[0])

    lo = min(y for _, y in pts)
    hi = max(y for _, y in pts)
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i else pts[0]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        c1 = (c1[0], min(max(c1[1], lo), hi))
        c2 = (c2[0], min(max(c2[1], lo), hi))
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def build():
    series = monthly(contrib.last_year())
    total = sum(c for _, c in series)
    peak = max(c for _, c in series)
    top = nice_ceiling(peak)

    n = len(series)
    xs = [L + (PW * i / (n - 1)) for i in range(n)] if n > 1 else [L + PW / 2]
    ys = [TOP + PH - (PH * c / top) for _, c in series]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{total} contributions over the last twelve months, by month">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{AREA}" stop-opacity="0.42"/>'
        f'<stop offset="1" stop-color="{AREA}" stop-opacity="0.02"/></linearGradient></defs>',
        f'<g font-family="{MONO}">',
        f'<text x="{L}" y="32" font-size="15" fill="{TEXT}">{total} contributions '
        f'<tspan fill="{MUTED}">over the last twelve months</tspan></text>',
    ]

    # horizontal gridlines, labelled on the left
    for i in range(5):
        v = top * i / 4
        y = TOP + PH - (PH * i / 4)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{L - 10}" y="{y + 3.5:.1f}" font-size="9.5" fill="{MUTED}" '
                   f'text-anchor="end">{int(v)}</text>')

    line = spline(list(zip(xs, ys)))
    area = f"{line} L{xs[-1]:.1f},{TOP + PH} L{xs[0]:.1f},{TOP + PH} Z"

    out.append(f'<path d="{area}" fill="url(#fade)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="{GREEN}" stroke-width="2" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')

    for (d, c), x, y in zip(series, xs, ys):
        # the busiest month gets the amber dot, so the eye lands somewhere
        colour = AMBER if c == peak else GREEN
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{BG}" stroke="{colour}" '
                   f'stroke-width="2"><title>{esc(f"{c} in {MONTHS[d.month - 1]} {d.year}")}'
                   f'</title></circle>')
        out.append(f'<text x="{x:.1f}" y="{TOP + PH + 22}" font-size="10" fill="{MUTED}" '
                   f'text-anchor="middle">{MONTHS[d.month - 1]}</text>')

    pd, _ = max(series, key=lambda s: s[1])
    out.append(f'<text x="{W - R}" y="32" font-size="10.5" fill="{MUTED}" text-anchor="end">'
               f'busiest <tspan fill="{AMBER}">{MONTHS[pd.month - 1]} {pd.year} · {peak}</tspan></text>')

    out.append("</g></svg>")
    return "".join(out)


if __name__ == "__main__":
    import sys

    dest = sys.argv[1] if len(sys.argv) > 1 else "assets/activity.svg"
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    svg = build()
    with io.open(dest, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", dest, len(svg), "bytes")
