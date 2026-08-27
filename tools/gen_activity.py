"""Build the recent activity chart.

Replaces github-readme-activity-graph, which now answers 402 (the hosted service
ran out of quota) and rendered as a broken image on the profile. Same idea, our
own palette, and the numbers come from the same public contribution endpoint the
calendar uses -- so the two visuals can never disagree.

Window is the last three months, plotted a day at a time. Three monthly buckets
would be three points, which is not a curve; daily resolution over a quarter is
what actually shows the shape of the work.
"""
import datetime as dt
import io
import os

import contrib
from theme import AMBER, BG, BORDER, MONO, MUTED, TEXT, esc

W, H = 900, 240
DAYS = 92                       # the window, in days
L, R = 52, 30                   # plot margins
TOP, BOT = 62, 46
PW = W - L - R
PH = H - TOP - BOT

GREEN = "#39d353"
AREA = "#26a641"
GRID = "#1e1e24"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def recent(days):
    """-> [(date, count)] for the last DAYS days, oldest first."""
    return [(dt.date.fromisoformat(iso), count) for iso, _, count in days][-DAYS:]


def month_ticks(series):
    """Label the first of each month, plus the window's own start day.

    The start label is dropped when a month boundary lands right after it,
    since the two would print on top of each other.
    """
    out, seen = [], series[0][0].month
    for i, (d, _) in enumerate(series):
        if d.month != seen:
            out.append((i, d))
            seen = d.month
    if not out or out[0][0] >= 8:
        out.insert(0, (0, series[0][0]))
    return out


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
    series = recent(contrib.last_year())
    total = sum(c for _, c in series)
    peak = max(c for _, c in series)
    peak_i = max(range(len(series)), key=lambda i: series[i][1])
    top = nice_ceiling(peak)

    n = len(series)
    xs = [L + (PW * i / (n - 1)) for i in range(n)]
    ys = [TOP + PH - (PH * c / top) for _, c in series]

    first, last = series[0][0], series[-1][0]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{total} contributions in the last three months, by day">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{AREA}" stop-opacity="0.42"/>'
        f'<stop offset="1" stop-color="{AREA}" stop-opacity="0.02"/></linearGradient></defs>',
        f'<g font-family="{MONO}">',
        f'<text x="{L}" y="32" font-size="15" fill="{TEXT}">{total} contributions '
        f'<tspan fill="{MUTED}">in the last three months</tspan></text>',
        f'<text x="{W - R}" y="32" font-size="10.5" fill="{MUTED}" text-anchor="end">'
        f'{MONTHS[first.month - 1]} {first.day} — {MONTHS[last.month - 1]} {last.day}</text>',
    ]

    for i in range(5):
        y = TOP + PH - (PH * i / 4)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{L - 10}" y="{y + 3.5:.1f}" font-size="9.5" fill="{MUTED}" '
                   f'text-anchor="end">{int(top * i / 4)}</text>')

    line = spline(list(zip(xs, ys)))
    area = f"{line} L{xs[-1]:.1f},{TOP + PH} L{xs[0]:.1f},{TOP + PH} Z"
    out.append(f'<path d="{area}" fill="url(#fade)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="{GREEN}" stroke-width="2" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')

    # a marker per day would be 92 dots; only the busiest one earns one
    px, py = xs[peak_i], ys[peak_i]
    pd = series[peak_i][0]
    out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{TOP + PH}" '
               f'stroke="{AMBER}" stroke-width="1" opacity="0.35"/>')
    out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="{BG}" stroke="{AMBER}" '
               f'stroke-width="2"><title>{esc(f"{peak} on {MONTHS[pd.month - 1]} {pd.day}")}'
               f'</title></circle>')
    anchor = "end" if px > W / 2 else "start"
    dx = -9 if anchor == "end" else 9
    out.append(f'<text x="{px + dx:.1f}" y="{py - 9:.1f}" font-size="10" fill="{AMBER}" '
               f'text-anchor="{anchor}">{peak} on {MONTHS[pd.month - 1]} {pd.day}</text>')

    for i, d in month_ticks(series):
        out.append(f'<text x="{xs[i]:.1f}" y="{TOP + PH + 22}" font-size="10" fill="{MUTED}" '
                   f'text-anchor="middle">{MONTHS[d.month - 1]} {d.day}</text>')

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
