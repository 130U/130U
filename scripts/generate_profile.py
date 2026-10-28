#!/usr/bin/env python3
"""Generate static profile assets from GitHub's public contribution calendar."""

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
CONFIG_PATH = ROOT / "profile.config.json"
OUTPUT_DIR = ROOT / "assets" / "generated"
LIVE_SOURCE = "GitHub public contribution calendar"

PALETTES = {
    "light": {
        "bg_a": "#F7F6F5", "bg_b": "#F7F6F5", "surface": "#F7F6F5", "surface_2": "#F7F6F5",
        "ink": "#191919", "muted": "#55534F", "faint": "#64605B", "line": "#DFDDD9", "blue": "#2200FF",
    },
    "dark": {
        "bg_a": "#151616", "bg_b": "#151616", "surface": "#151616", "surface_2": "#151616",
        "ink": "#F2F0EB", "muted": "#C5C2BC", "faint": "#ACA9A3", "line": "#343737", "blue": "#AEA2FF",
    },
}

TELEMETRY_PALETTES = {
    theme: {
        "background": palette["bg_a"], "number": palette["ink"], "title": palette["ink"],
        "description": palette["muted"], "timestamp": palette["faint"],
    }
    for theme, palette in PALETTES.items()
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


def rails(width: int, height: int, color: str, *, mobile: bool) -> str:
    positions = (28, 80, width - 28) if mobile else (44, 232, 276, width - 44)
    return "\n".join(
        f'<path d="M{x} 0 V{height}" fill="none" stroke="{color}" stroke-width="1"/>'
        f'<path d="M{x} 0 V8 M{x} {height - 8} V{height}" fill="none" stroke="{color}" stroke-width="2"/>'
        for x in positions
    )


def hatch(x: int, y: int, width: int, height: int, color: str) -> str:
    """A quiet engraved patch, independent of the contribution data."""
    lines = []
    for offset in range(0, width + height, 12):
        start_x, start_y = max(0, offset - height), min(height, offset)
        end_x, end_y = min(width, offset), max(0, offset - width)
        lines.append(f'M{x + start_x} {y + start_y} L{x + end_x} {y + end_y}')
    return f'<path d="{" ".join(lines)}" fill="none" stroke="{color}" stroke-width="0.7"/>'


def hero_svg(config: dict, theme: str, *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    identity = config["identity"]
    width, height = (640, 360) if mobile else (1200, 320)
    parts = [svg_start(width, height, "Theodore Ouyang — AI Engineering & Finance",
                       "Models, agents, and mathematical research. Two areas: AI Engineering and Finance."),
             f'<rect width="{width}" height="{height}" fill="{p["bg_a"]}"/>',
             rails(width, height, p["line"], mobile=mobile)]
    if mobile:
        parts.extend([
            text(100, 53, "130U / RESEARCH & ENGINEERING", 17, p["faint"], family="mono"),
            text(100, 125, identity["name"], 46, p["ink"], tracking=-1.5),
            text(100, 185, "AI Engineering", 35, p["ink"], family="serif"),
            text(100, 226, "& Finance", 35, p["ink"], family="serif"),
            text(100, 293, "Models, agents, and", 22, p["muted"], family="serif"),
            text(100, 321, "mathematical research.", 22, p["muted"], family="serif"),
            f'<path d="M43 92 H63 M53 82 V102" stroke="{p["blue"]}" stroke-width="1.5"/>',
            hatch(472, 177, 112, 62, p["line"]),
        ])
    else:
        parts.extend([
            text(64, 68, "130U", 23, p["ink"], family="mono"),
            text(64, 236, "RESEARCH", 14, p["faint"], family="mono", tracking=1),
            text(64, 258, "& ENGINEERING", 14, p["faint"], family="mono", tracking=1),
            text(245, 81, "00", 14, p["faint"], family="mono"),
            text(310, 110, identity["name"], 56, p["ink"], tracking=-1.8),
            text(312, 168, "AI Engineering & Finance", 34, p["ink"], family="serif"),
            text(312, 214, "Models, agents, and mathematical research.", 24, p["muted"], family="serif"),
            f'<path d="M312 255 H1108" stroke="{p["line"]}"/>',
            f'<path d="M312 255 H340" stroke="{p["blue"]}" stroke-width="2"/>',
            text(312, 286, "01 / AI ENGINEERING", 15, p["faint"], family="mono"),
            text(660, 286, "02 / FINANCE", 15, p["faint"], family="mono"),
            hatch(975, 67, 130, 126, p["line"]),
        ])
    parts.append("</svg>\n")
    return "\n".join(parts)


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


def telemetry_svg(config: dict, data: dict, theme: str, generated_at: datetime,
                  *, mobile: bool = False) -> str:
    p = TELEMETRY_PALETTES[theme]
    palette = PALETTES[theme]
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
             f'<rect width="{width}" height="{height}" fill="{p["background"]}"/>',
             rails(width, height, palette["line"], mobile=mobile)]
    if mobile:
        parts.extend([
            text(100, 46, "GITHUB / ACTIVITY", 17, p["timestamp"], family="mono"),
            text(100, 117, f'{recent["total"]:,}', 60, p["number"], tracking=-2),
            text(270, 88, "contributions", 26, p["title"]),
            text(270, 119, "Last 30 days", 20, p["description"], family="mono"),
            text(100, 260, snapshot, 18, p["timestamp"], family="mono"),
        ])
        x, y, w, h = 100, 156, 478, 57
    else:
        parts.extend([
            text(64, 55, "GITHUB", 15, p["timestamp"], family="mono", tracking=1),
            text(64, 79, "/ ACTIVITY", 15, p["timestamp"], family="mono", tracking=1),
            text(310, 89, f'{recent["total"]:,}', 62, p["number"], tracking=-2),
            text(476, 62, "contributions", 25, p["title"]),
            text(476, 94, "Last 30 days", 18, p["description"], family="mono"),
            text(312, 138, snapshot, 16, p["timestamp"], family="mono"),
            text(1108, 138, "DAILY CONTRIBUTIONS", 13, p["timestamp"], family="mono", anchor="end"),
        ])
        x, y, w, h = 800, 42, 308, 56
    points = contribution_sparkline_points(data, x=x, y=y, width=w, height=h)
    path = "M" + " L".join(f"{px:.2f} {py:.2f}" for px, py in points)
    parts.extend([
        f'<path d="M{x} {y + h} H{x + w}" stroke="{palette["line"]}" fill="none"/>',
        f'<path id="contribution-sparkline" d="{path}" stroke="{palette["blue"]}" '
        'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" fill="none"/>',
        "</svg>\n",
    ])
    return "\n".join(parts)


def build_assets(config: dict, data: dict, generated_at: datetime) -> dict[str, str]:
    assets = {}
    for theme in ("light", "dark"):
        for mobile in (False, True):
            variant = f"mobile-{theme}" if mobile else theme
            assets[f"hero-{variant}-v5.svg"] = hero_svg(config, theme, mobile=mobile)
            assets[f"telemetry-{variant}-v5.svg"] = telemetry_svg(config, data, theme, generated_at, mobile=mobile)
    return assets


def write_assets(config: dict, data: dict, generated_at: datetime | None = None) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in build_assets(config, data, generated_at).items():
        (OUTPUT_DIR / filename).write_text(content, encoding="utf-8", newline="\n")


def save_live_snapshot(config: dict, data: dict, collected_at: datetime) -> None:
    if data["source"] == LIVE_SOURCE:
        config["fallback_contributions"] = {key: data[key] for key in ("total", "days", "range_start", "range_end")}
        config["snapshot_updated_at"] = collected_at.isoformat().replace("+00:00", "Z")
        CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch GitHub's public profile contribution count")
    args = parser.parse_args()
    config = load_config()
    data = resolve_profile_data(config, args.live)
    generated_at = datetime.now(timezone.utc)
    save_live_snapshot(config, data, generated_at)
    write_assets(config, data, generated_at)
    recent = contributions_last_30_days(data)
    print(f'Generated eight static SVG assets from {data["source"]}: '
          f'{recent["total"]:,} contributions in the last 30 days '
          f'({recent["range_start"]} through {recent["range_end"]}).')


if __name__ == "__main__":
    main()
