#!/usr/bin/env python3
"""Generate the profile's contribution line from GitHub's public contribution calendar."""

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
TYPE_PATH = ROOT / "config" / "type.json"
OUTPUT_DIR = ROOT / "assets" / "generated"
LIVE_SOURCE = "GitHub public contribution calendar"
PANEL = "contributions.svg"

# The line is drawn for a light and a dark page; "page" is the ground each theme is read against.
THEMES = {
    "light": {"page": "#ffffff", "ink": "#0b0b0b", "muted": "#70706c", "accent": "#2200ff",
              "line": "#000000", "rule": 0.22, "dash": 0.17},
    "dark": {"page": "#0d1117", "ink": "#f1f0ee", "muted": "#94938d", "accent": "#9d8cff",
             "line": "#ffffff", "rule": 0.30, "dash": 0.22},
}
# The ledger's three widths. "left" is its title axis; the wide layout sets the trace on its prose axis.
LAYOUTS = {
    "wide": {"width": 846, "scale": 2, "left": 24, "trace": (370, 36, 452, 26), "stamp": (370, 80), "height": 96},
    "medium": {"width": 520, "scale": 3, "left": 26, "trace": (26, 102, 468, 40), "stamp": (26, 168), "height": 184},
    "narrow": {"width": 330, "scale": 4, "left": 20, "trace": (20, 102, 290, 40), "stamp": (20, 168), "height": 184},
}
GAP = 40                      # space above the rule, as above every section of the ledger
NUMBER = {"size": 24, "tracking": -0.015, "baseline": 56}
LABEL = {"size": 13, "tracking": 0.015, "baseline": 80}
MEASURE = "Contributions in the last 30 days"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_type() -> dict:
    return json.loads(TYPE_PATH.read_text(encoding="utf-8"))


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


def trim(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


class Sheet:
    """One static SVG whose type is drawn from the outlines in config/type.json."""

    def __init__(self, width: int, height: int, scale: int, theme: str, face: dict) -> None:
        self.width, self.height, self.scale = width, height, scale
        self.theme, self.face = THEMES[theme], face
        self.outlines: dict[str, str] = {}
        self.body: list[str] = []

    def text(self, value: str, x: float, baseline: float, size: float, color: str, tracking: float = 0.0) -> None:
        """Set one line: advances and pair kerning place each letter, in font units."""
        units = self.face["units_per_em"]
        factor = size / units
        pen, uses = 0.0, []
        for index, character in enumerate(value):
            advance, outline = self.face["glyphs"][character]
            if index:
                pen += self.face["kerning"].get(value[index - 1] + character, 0)
            if outline:
                name = f"g{ord(character):x}"
                self.outlines[name] = outline
                uses.append(f'<use href="#{name}" x="{round(pen)}"/>')
            pen += advance + tracking * units
        self.body.append(
            f'<g data-text="{escape(value, quote=True)}" fill="{self.theme[color]}" '
            f'transform="translate({trim(x)} {trim(baseline)}) scale({factor:.6f} {-factor:.6f})">'
            + "".join(uses) + "</g>")

    def stroke(self, path: str, kind: str, *, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="4 4"' if dashed else ""
        self.body.append(f'<path d="{path}" stroke="{self.theme["line"]}" stroke-opacity="{self.theme[kind]}" '
                         f'fill="none"{dash}/>')

    def render(self, title: str, description: str) -> str:
        outlines = "".join(f'<path id="{name}" d="{outline}"/>' for name, outline in sorted(self.outlines.items()))
        return "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width * self.scale}" '
            f'height="{self.height * self.scale}" viewBox="0 0 {self.width} {self.height}" '
            'role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            f"<defs>{outlines}</defs>",
            *self.body,
            "</svg>",
            "",
        ])


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


def contributions_svg(data: dict, generated_at: datetime, *, layout: str = "wide", theme: str = "light",
                      face: dict | None = None) -> str:
    spec, colors = LAYOUTS[layout], THEMES[theme]
    saved = data["source"] != LIVE_SOURCE
    timestamp = data["snapshot_at"] if saved else generated_at.isoformat()
    stamp = ("Saved snapshot " if saved else "Updated ") + parse_utc(timestamp).strftime("%d %b %Y UTC")
    recent = contributions_last_30_days(data)
    sheet = Sheet(spec["width"], GAP + spec["height"], spec["scale"], theme, face or load_type())
    sheet.stroke(f'M0 {GAP + 0.5}H{spec["width"]}', "rule")
    sheet.text(f'{recent["total"]:,}', spec["left"], GAP + NUMBER["baseline"], NUMBER["size"], "ink",
               NUMBER["tracking"])
    sheet.text(MEASURE, spec["left"], GAP + LABEL["baseline"], LABEL["size"], "muted", LABEL["tracking"])
    stamp_x, stamp_baseline = spec["stamp"]
    sheet.text(stamp, stamp_x, GAP + stamp_baseline, LABEL["size"], "muted", LABEL["tracking"])
    x, y, width, height = spec["trace"]
    y += GAP
    points = contribution_sparkline_points(data, x=x, y=y, width=width, height=height)
    sheet.stroke(f"M{x} {y + height + 0.5}H{x + width}", "dash", dashed=True)
    sheet.body.append(
        '<path id="contribution-sparkline" d="M' + " L".join(f"{px:.2f} {py:.2f}" for px, py in points)
        + f'" stroke="{colors["ink"]}" stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round" fill="none"/>')
    last_x, last_y = points[-1]
    sheet.body.append(f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="2.75" fill="{colors["accent"]}"/>')
    return sheet.render(
        "130U — GitHub contributions",
        f'{recent["total"]:,} GitHub contributions in the last 30 days '
        f'({recent["range_start"]} through {recent["range_end"]}, inclusive). '
        f'The line plots daily counts on a zero baseline. {stamp}.')


def build_assets(data: dict, generated_at: datetime) -> dict[str, str]:
    """The line at each of the ledger's widths, light and dark, keyed by its folder under assets/generated."""
    face = load_type()
    return {
        (layout if theme == "light" else f"{layout}-dark"):
            contributions_svg(data, generated_at, layout=layout, theme=theme, face=face)
        for layout in LAYOUTS for theme in THEMES
    }


def write_assets(data: dict, generated_at: datetime | None = None) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    for folder, content in build_assets(data, generated_at).items():
        (OUTPUT_DIR / folder).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / folder / PANEL).write_text(content, encoding="utf-8", newline="\n")


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
    print(f'Generated {len(LAYOUTS) * len(THEMES)} static SVG assets from {data["source"]}: '
          f'{recent["total"]:,} contributions in the last 30 days '
          f'({recent["range_start"]} through {recent["range_end"]}).')


if __name__ == "__main__":
    main()
