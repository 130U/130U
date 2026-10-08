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
        "bg_a": "#F6F7F9", "bg_b": "#F6F7F9", "surface": "#FFFFFF", "surface_2": "#F6F7F9",
        "ink": "#1D1D1F", "muted": "#505056", "faint": "#626269", "line": "#D5D7DC", "blue": "#2455A4",
    },
    "dark": {
        "bg_a": "#16181D", "bg_b": "#16181D", "surface": "#1D2026", "surface_2": "#16181D",
        "ink": "#F5F5F7", "muted": "#C2C5CD", "faint": "#ADB2BF", "line": "#3B414D", "blue": "#9BBCF7",
    },
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
        return collect_live_data(config)
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
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }\n'
        '  </style>\n'
    )


def text(x: int, y: int, value: str, size: int, color: str, *, weight: int = 400,
         tracking: float = 0, anchor: str = "start") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" letter-spacing="{tracking}" text-anchor="{anchor}">'
            f'{escape(value)}</text>')


def hero_svg(config: dict, theme: str, *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    identity = config["identity"]
    width, height = (640, 420) if mobile else (1200, 320)
    parts = [svg_start(width, height, "130U — Artificial Intelligence and Engineering",
                       "Artificial intelligence and engineering, with earlier research in mathematical finance."),
             f'<rect width="{width}" height="{height}" rx="20" fill="{p["bg_a"]}"/>']
    if mobile:
        parts.extend([
            text(40, 58, identity["eyebrow"], 22, p["muted"], weight=600, tracking=1),
            text(38, 143, identity["headline"], 51, p["ink"], weight=650, tracking=-1.7),
            text(38, 207, identity["subheadline"], 51, p["ink"], weight=650, tracking=-1.7),
            f'<path d="M40 248 H600" stroke="{p["line"]}"/>',
            text(40, 299, "Agent evaluation. Applied AI.", 26, p["muted"]),
            text(40, 339, "Research tools and intelligent systems.", 26, p["muted"]),
            text(40, 389, "Earlier research · Mathematical finance", 22, p["faint"]),
        ])
    else:
        parts.extend([
            text(56, 57, identity["eyebrow"], 19, p["muted"], weight=600, tracking=1.3),
            text(53, 139, identity["headline"], 65, p["ink"], weight=650, tracking=-2.2),
            text(53, 215, identity["subheadline"], 65, p["ink"], weight=650, tracking=-2.2),
            text(56, 274, identity["descriptor"], 22, p["muted"]),
            f'<path d="M810 74 V248" stroke="{p["line"]}"/>',
            text(850, 104, "AI SYSTEMS & TOOLS", 18, p["blue"], weight=600, tracking=.8),
            text(850, 141, "Agent evaluation", 25, p["ink"], weight=500),
            text(850, 175, "Research workflows", 25, p["ink"], weight=500),
            text(850, 230, "EARLIER RESEARCH", 18, p["muted"], weight=600, tracking=.5),
            text(850, 263, "Mathematical finance", 25, p["ink"]),
        ])
    parts.append("</svg>\n")
    return "\n".join(parts)


def telemetry_svg(config: dict, data: dict, theme: str, generated_at: datetime,
                  *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    width, height = (640, 260) if mobile else (1200, 180)
    saved = data["source"] != LIVE_SOURCE
    timestamp = data["snapshot_at"] if saved else generated_at.isoformat()
    timestamp_label = parse_utc(timestamp).strftime("%d %b %Y UTC")
    snapshot = ("Saved snapshot" if saved else "Updated") + " · " + timestamp_label
    parts = [svg_start(width, height, "130U — GitHub contributions",
                       f'{data["total"]:,} GitHub contributions in the last year. {snapshot}.'),
             f'<rect width="{width}" height="{height}" rx="16" fill="{p["bg_a"]}"/>']
    if mobile:
        parts.extend([
            text(40, 100, f'{data["total"]:,}', 80, p["ink"], weight=650, tracking=-2),
            text(40, 151, "GitHub contributions", 32, p["ink"], weight=500),
            text(40, 190, "In the last year", 25, p["muted"]),
            text(40, 233, snapshot, 20, p["faint"]),
        ])
    else:
        parts.extend([
            text(48, 110, f'{data["total"]:,}', 82, p["ink"], weight=650, tracking=-2),
            text(330, 83, "GitHub contributions", 32, p["ink"], weight=500),
            text(330, 119, "In the last year", 23, p["muted"]),
            text(1152, 156, snapshot, 17, p["faint"], anchor="end"),
        ])
    parts.append("</svg>\n")
    return "\n".join(parts)


def build_assets(config: dict, data: dict, generated_at: datetime) -> dict[str, str]:
    assets = {}
    for theme in ("light", "dark"):
        for mobile in (False, True):
            variant = f"mobile-{theme}" if mobile else theme
            assets[f"hero-{variant}-v3.svg"] = hero_svg(config, theme, mobile=mobile)
            assets[f"telemetry-{variant}-v3.svg"] = telemetry_svg(config, data, theme, generated_at, mobile=mobile)
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
    print(f'Generated eight static SVG assets from {data["source"]}: {data["total"]:,} contributions.')


if __name__ == "__main__":
    main()
