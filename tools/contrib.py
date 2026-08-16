"""Read the real contribution calendar off GitHub's public endpoint.

No token required. The same numbers GitHub prints on the profile page.
"""
import datetime as dt
import re
import urllib.request

USER = "Niloy-Bhuiyan"
URL = "https://github.com/users/{}/contributions"

CELL = re.compile(
    r'<td[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"[^>]*id="([^"]+)"'
    r'|<td[^>]*id="([^"]+)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"'
)
TIP = re.compile(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>')


def _fetch(params=""):
    req = urllib.request.Request(URL.format(USER) + params, headers={"User-Agent": "profile-build"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def _parse(html):
    """-> list of (date, level, count), ordered by date."""
    counts = {}
    for cid, text in TIP.findall(html):
        m = re.match(r"([\d,]+)\s+contribution", text.strip())
        counts[cid] = int(m.group(1).replace(",", "")) if m else 0

    days = []
    for td in re.findall(r"<td[^>]*class=\"ContributionCalendar-day\"[^>]*>", html):
        d = re.search(r'data-date="([^"]+)"', td)
        lv = re.search(r'data-level="(\d)"', td)
        cid = re.search(r'id="([^"]+)"', td)
        if not (d and lv):
            continue
        days.append((d.group(1), int(lv.group(1)), counts.get(cid.group(1) if cid else "", 0)))
    days.sort()
    return days


def last_year():
    return _parse(_fetch())


def year(y):
    return _parse(_fetch(f"?from={y}-01-01&to={y}-12-31"))


def year_totals(first=2023):
    this = dt.date.today().year
    out = []
    for y in range(this, first - 1, -1):
        total = sum(c for _, _, c in year(y))
        out.append((y, total))
    return out


if __name__ == "__main__":
    days = last_year()
    print("last year:", len(days), "days, total", sum(c for _, _, c in days))
    print("range:", days[0][0], "->", days[-1][0])
    print("levels:", sorted({l for _, l, _ in days}))
    print()
    for y, t in year_totals():
        print(f"  {y}: {t}")
