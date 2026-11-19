#!/usr/bin/env python3
"""Generate the profile's contribution panel from GitHub's public contribution calendar."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "profile.json"
OUTPUT_DIR = ROOT / "assets" / "generated"
LIVE_SOURCE = "GitHub public contribution calendar"

PALETTE = {
    "background": "#0A0A09", "ink": "#F3EEE3", "muted": "#B9B2A3", "faint": "#8B8578",
    "line": "#3A3324", "gold": "#C4A45C",
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class ContributionParser(HTMLParser):
    """Read the official total and each cell's count, independent of DOM order."""

    def __init__(self) -> None:
        super().__init__()
        self.cells: dict[str, dict] = {}
        self.tooltips: dict[str, str] = {}
        self.heading = ""
        self.capture: tuple[str, str] | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "td" and "data-date" in attributes:
            cell_id = attributes.get("id")
            if not cell_id or cell_id in self.cells:
                raise ValueError("Contribution calendar has a missing or duplicate cell ID")
            self.cells[cell_id] = {
                "date": attributes["data-date"],
                "level": int(attributes["data-level"]),
            }
        elif tag == "tool-tip" and (attributes.get("for") or "").startswith("contribution-day-component-"):
            self.capture = ("tooltip", attributes["for"])
            self.buffer = []
        elif tag == "h2" and attributes.get("id") == "js-contribution-activity-description":
            self.capture = ("heading", "")
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.capture:
            return
        kind, cell_id = self.capture
        if (kind == "tooltip" and tag == "tool-tip") or (kind == "heading" and tag == "h2"):
            value = " ".join("".join(self.buffer).split())
            if kind == "tooltip":
                if cell_id in self.tooltips:
                    raise ValueError("Contribution calendar has a duplicate tooltip")
                self.tooltips[cell_id] = value
            else:
                self.heading = value
            self.capture = None

    def result(self) -> dict:
        heading = re.fullmatch(r"([\d,]+) contributions? in the last year", self.heading)
        if not heading or not self.cells:
            raise ValueError("GitHub's public contribution calendar is incomplete")
        total = int(heading[1].replace(",", ""))
        days = []
        for cell_id, cell in self.cells.items():
            tooltip = self.tooltips.get(cell_id, "")
            count_match = re.match(r"^([\d,]+) contributions? on ", tooltip)
            if tooltip.startswith("No contributions on "):
                count = 0
            elif count_match:
                count = int(count_match[1].replace(",", ""))
            else:
                raise ValueError(f"Missing contribution count for {cell['date']}")
            day_date = date.fromisoformat(cell["date"])
            if day_date.isoformat() != cell["date"] or not 0 <= cell["level"] <= 4:
                raise ValueError("Invalid contribution calendar date or intensity")
            days.append({**cell, "count": count})
        days.sort(key=lambda day: day["date"])
        start = date.fromisoformat(days[0]["date"])
        expected = [(start + timedelta(days=index)).isoformat() for index in range(len(days))]
        if [day["date"] for day in days] != expected:
            raise ValueError("Contribution calendar dates are not unique and continuous")
        if sum(day["count"] for day in days) != total:
            raise ValueError("Contribution calendar total does not match daily counts")
        return {"total": total, "days": days, "range_start": days[0]["date"], "range_end": days[-1]["date"]}


def parse_contributions(html: str) -> dict:
    parser = ContributionParser()
    parser.feed(html)
    return parser.result()


def contributions_last_30_days(data: dict) -> dict:
    """Sum 30 calendar dates, including the latest date in GitHub's calendar."""
    end = date.fromisoformat(data["range_end"])
    start = end - timedelta(days=29)
    days = [day for day in data["days"] if start.isoformat() <= day["date"] <= end.isoformat()]
    expected_dates = {(start + timedelta(days=index)).isoformat() for index in range(30)}
    if len(days) != 30 or {day["date"] for day in days} != expected_dates:
        raise ValueError("Contribution calendar does not cover the complete 30-day window")
    if any(type(day["count"]) is not int or day["count"] < 0 for day in days):
        raise ValueError("Contribution counts must be nonnegative integers")
    return {"total": sum(day["count"] for day in days),
            "range_start": start.isoformat(), "range_end": end.isoformat()}


def collect_live_data(config: dict) -> dict:
    username = urllib.parse.quote(config["username"], safe="")
    request = urllib.request.Request(
        f"https://github.com/users/{username}/contributions",
        headers={"User-Agent": "130U-profile-generator", "Accept-Language": "en-US"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    return {**parse_contributions(html), "source": LIVE_SOURCE}


def collect_snapshot_data(config: dict) -> dict:
    return {**config["fallback_contributions"], "source": "verified local snapshot",
            "snapshot_at": config["snapshot_updated_at"]}


def resolve_profile_data(config: dict, live: bool) -> dict:
    if not live:
        return collect_snapshot_data(config)
    try:
        data = collect_live_data(config)
        contributions_last_30_days(data)
        return data
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        reason = f"HTTP {error.code}" if isinstance(error, urllib.error.HTTPError) else error.__class__.__name__
        print(f"GitHub contribution calendar unavailable ({reason}); using the verified saved snapshot.", file=sys.stderr)
        return collect_snapshot_data(config)


def svg_start(width: int, height: int, title: str, description: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{escape(title)}</title>\n'
        f'  <desc id="desc">{escape(description)}</desc>\n'
        '  <!-- Generated by scripts/generate_profile.py. Static, self-contained SVG. -->\n'
        '  <style>\n'
        '    text { font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif; }\n'
        '    .serif { font-family: Georgia, "Times New Roman", serif; }\n'
        '    .mono { font-family: Consolas, "Liberation Mono", monospace; }\n'
        '  </style>\n'
    )


def text(x: float, y: float, value: str, size: int, color: str, *, weight: int = 400,
         tracking: float = 0, anchor: str = "start", family: str = "sans") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" class="{family}" '
            f'font-weight="{weight}" letter-spacing="{tracking}" text-anchor="{anchor}">'
            f'{escape(value)}</text>')


def contribution_sparkline_points(data: dict, *, x: float, y: float,
                                 width: float, height: float) -> list[tuple[float, float]]:
    """Plot the same 30 dates as the total; zero lies on a common baseline."""
    if width <= 0 or height <= 0:
        raise ValueError("Sparkline dimensions must be positive")
    recent = contributions_last_30_days(data)
    days = sorted(
        (day for day in data["days"] if recent["range_start"] <= day["date"] <= recent["range_end"]),
        key=lambda day: day["date"],
    )
    counts = [day["count"] for day in days]
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError("Contribution counts must be nonnegative integers")
    peak = max(counts) or 1
    return [(x + index * width / 29, y + height - count * height / peak)
            for index, count in enumerate(counts)]


def contributions_svg(data: dict, generated_at: datetime, *, mobile: bool = False) -> str:
    p = PALETTE
    width, height = (640, 292) if mobile else (1200, 170)
    saved = data["source"] != LIVE_SOURCE
    timestamp = data["snapshot_at"] if saved else generated_at.isoformat()
    timestamp_label = parse_utc(timestamp).strftime("%d %b %Y UTC")
    snapshot = ("Saved snapshot" if saved else "Updated") + " · " + timestamp_label
    recent = contributions_last_30_days(data)
    parts = [svg_start(width, height, "130U — GitHub contributions",
                       f'{recent["total"]:,} GitHub contributions in the last 30 days '
                       f'({recent["range_start"]} through {recent["range_end"]}, inclusive). '
                       f'The line plots daily counts on a zero baseline. {snapshot}.'),
             f'<rect width="{width}" height="{height}" fill="{p["background"]}"/>']
    if mobile:
        parts.extend([
            text(48, 46, "GITHUB / ACTIVITY", 17, p["gold"], family="mono", tracking=1),
            text(48, 117, f'{recent["total"]:,}', 60, p["ink"], family="serif", tracking=-1),
            text(222, 88, "contributions", 26, p["ink"]),
            text(222, 119, "Last 30 days", 20, p["muted"], family="mono"),
            text(48, 260, snapshot, 18, p["faint"], family="mono"),
        ])
        x, y, w, h = 48, 156, 544, 57
    else:
        parts.extend([
            text(48, 55, "GITHUB", 15, p["gold"], family="mono", tracking=1),
            text(48, 79, "/ ACTIVITY", 15, p["gold"], family="mono", tracking=1),
            text(294, 91, f'{recent["total"]:,}', 62, p["ink"], family="serif", tracking=-1),
            text(470, 62, "contributions", 25, p["ink"]),
            text(470, 94, "Last 30 days", 18, p["muted"], family="mono"),
            text(296, 138, snapshot, 16, p["faint"], family="mono"),
            text(1152, 138, "DAILY CONTRIBUTIONS", 13, p["faint"], family="mono", anchor="end"),
        ])
        x, y, w, h = 844, 42, 308, 56
    points = contribution_sparkline_points(data, x=x, y=y, width=w, height=h)
    path = "M" + " L".join(f"{px:.2f} {py:.2f}" for px, py in points)
    parts.extend([
        f'<path d="M{x} {y + h} H{x + w}" stroke="{p["line"]}" fill="none"/>',
        f'<path id="contribution-sparkline" d="{path}" stroke="{p["gold"]}" '
        'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" fill="none"/>',
        "</svg>\n",
    ])
    return "\n".join(parts)


def build_assets(data: dict, generated_at: datetime) -> dict[str, str]:
    return {
        "contributions.svg": contributions_svg(data, generated_at),
        "contributions-mobile.svg": contributions_svg(data, generated_at, mobile=True),
    }


def write_assets(data: dict, generated_at: datetime | None = None) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in build_assets(data, generated_at).items():
        (OUTPUT_DIR / filename).write_text(content, encoding="utf-8", newline="\n")


def save_live_snapshot(config: dict, data: dict, collected_at: datetime) -> None:
    if data["source"] == LIVE_SOURCE:
        config["fallback_contributions"] = {key: data[key] for key in ("total", "days", "range_start", "range_end")}
        config["snapshot_updated_at"] = collected_at.isoformat().replace("+00:00", "Z")
        CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch GitHub's public profile contribution count")
    args = parser.parse_args()
    config = load_config()
    data = resolve_profile_data(config, args.live)
    generated_at = datetime.now(timezone.utc)
    save_live_snapshot(config, data, generated_at)
    write_assets(data, generated_at)
    recent = contributions_last_30_days(data)
    print(f'Generated two static SVG assets from {data["source"]}: '
          f'{recent["total"]:,} contributions in the last 30 days '
          f'({recent["range_start"]} through {recent["range_end"]}).')


if __name__ == "__main__":
    main()
