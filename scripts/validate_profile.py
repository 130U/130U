#!/usr/bin/env python3
"""Validate the profile: the README equals its build, every card has its cover, and the contribution panel is sound."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_readme  # noqa: E402
from generate_profile import PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "config" / "profile.json"
GENERATED = ROOT / "assets" / "generated"
COVERS = ROOT / "assets" / "covers"
EXPECTED_ASSETS = {"telemetry-v6.svg", "telemetry-mobile-v6.svg"}
HERO_ASSETS = ("hero.webp", "hero-mobile.webp")
EXPECTED_SECTIONS = ("research", "engineering", "law", "blog", "me")
SITE_REPOSITORY = "130U.github.io"
FORBIDDEN_SVG_MARKERS = ("<script", "javascript:", "data:text/html")


def fail(message: str) -> None:
    raise AssertionError(message)


class ReadmeLinks(HTMLParser):
    """Collect the anchors, links and images of the README in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[str] = []
        self.links: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.tables = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("id"):
            self.anchors.append(attributes["id"])
        elif tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        elif tag == "img":
            self.images.append((attributes.get("src", ""), attributes.get("alt", "")))
        elif tag == "table":
            self.tables += 1


def validate_sections(config: dict) -> None:
    identity = config.get("identity", {})
    if not identity.get("name") or not identity.get("line"):
        fail("Configuration must name the author and give the positioning line")
    sections = config.get("sections")
    if not isinstance(sections, list) or tuple(data.get("id") for data in sections) != EXPECTED_SECTIONS:
        fail("Configuration must list the five sections in order: " + ", ".join(EXPECTED_SECTIONS))
    seen_repositories: set[str] = set()
    seen_covers: set[str] = set()
    for data in sections:
        if not data.get("title") or not data.get("blurb") or not data.get("items"):
            fail(f'Section {data["id"]} needs a title, a blurb and at least one work')
        for item in data["items"]:
            for field in ("repository", "title", "line", "cover"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    fail(f'A work in {data["id"]} lacks its {field}')
            if item["repository"] in seen_repositories or item["cover"] in seen_covers:
                fail(f'{item["repository"]} or its cover appears twice')
            seen_repositories.add(item["repository"])
            seen_covers.add(item["cover"])
            if not re.fullmatch(r"[A-Za-z0-9._-]+", item["repository"]) or not re.fullmatch(r"[a-z0-9-]+", item["cover"]):
                fail(f'{item["repository"]} has an invalid repository or cover name')
            if not (COVERS / f'{item["cover"]}.webp').is_file():
                fail(f'{item["repository"]} has no cover image at assets/covers/{item["cover"]}.webp')
            if "url" in item and item["repository"] != SITE_REPOSITORY:
                fail("Only the personal website may link outside its repository")
    on_disk = {path.stem for path in COVERS.glob("*.webp")}
    if on_disk != seen_covers:
        fail(f"Cover images and listed works differ: {sorted(on_disk ^ seen_covers)}")


def validate_readme() -> None:
    text = README.read_text(encoding="utf-8")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if re.search(r"[㐀-鿿豈-﫿]", text):
        fail("README must remain English-only; CJK characters were found")
    if text != build_readme.build(config):
        fail("README.md differs from its build; run scripts/build_readme.py")
    parser = ReadmeLinks()
    parser.feed(text)
    parser.close()
    if tuple(parser.anchors) != EXPECTED_SECTIONS:
        fail("README must anchor the five sections in order")
    if parser.tables != len(EXPECTED_SECTIONS):
        fail("README must hold exactly one grid of works per section")
    if text.count(build_readme.ACTIVITY_MARKER) != 1 or text.index(build_readme.ACTIVITY_MARKER) < text.rindex("</table>"):
        fail("README must place one activity footer after the last section")
    expected_links = [build_readme.target(item) for data in config["sections"] for item in data["items"]]
    card_links = [link for link in parser.links if not link.startswith("#")]
    if card_links != [link for link in expected_links for _ in range(2)]:
        fail("README work ordering or link destination differs from the configuration")
    for source, alt in parser.images:
        if not alt:
            fail("README images need alternative text")
        if not source.startswith("assets/") or not (ROOT / source).is_file():
            fail(f"README image is not a local asset: {source}")
    for name in HERO_ASSETS:
        if not (ROOT / "assets" / name).is_file():
            fail(f"Missing hero image assets/{name}")


def validate_config() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data["username"] != "130U":
        fail("Profile repository must target exactly 130U")
    validate_sections(data)
    snapshot_at = data.get("snapshot_updated_at")
    try:
        snapshot = datetime.fromisoformat(snapshot_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        fail("Fallback metrics require a valid snapshot_updated_at timestamp")
    if snapshot.tzinfo is None or snapshot.utcoffset() is None:
        fail("Fallback snapshot_updated_at must identify its timezone")
    if snapshot > datetime.now(snapshot.tzinfo):
        fail("Fallback snapshot_updated_at must not claim a future data collection time")
    contributions = data.get("fallback_contributions")
    if not isinstance(contributions, dict):
        fail("Configuration must provide a fallback_contributions object")
    total = contributions.get("total")
    days = contributions.get("days")
    if type(total) is not int or total < 0:
        fail("Fallback contribution total must be a nonnegative integer")
    if not isinstance(days, list):
        fail("Fallback contribution days must be a list")

    def calendar_date(value: object, label: str) -> date:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            fail(f"{label} must use YYYY-MM-DD")
        try:
            return date.fromisoformat(value)
        except ValueError:
            fail(f"{label} is not a valid calendar date")

    range_start = calendar_date(contributions.get("range_start"), "Fallback range_start")
    range_end = calendar_date(contributions.get("range_end"), "Fallback range_end")
    if range_start > range_end:
        fail("Fallback contribution range_start must not follow range_end")
    seen_dates: set[date] = set()
    daily_total = 0
    for day in days:
        if not isinstance(day, dict):
            fail("Every fallback contribution day must be an object")
        day_date = calendar_date(day.get("date"), "Fallback contribution date")
        if day_date in seen_dates:
            fail("Fallback contribution dates must be unique")
        if not range_start <= day_date <= range_end:
            fail("Fallback contribution date lies outside its declared range")
        count, level = day.get("count"), day.get("level")
        if type(count) is not int or count < 0:
            fail("Fallback daily contribution count must be a nonnegative integer")
        if type(level) is not int or not 0 <= level <= 4:
            fail("Fallback contribution level must be an integer from 0 to 4")
        seen_dates.add(day_date)
        daily_total += count
    if daily_total != total:
        fail("Fallback contribution total must equal the sum of daily counts")
    if len(seen_dates) < 30:
        fail("Fallback contribution calendar must contain at least thirty days")
    if len(seen_dates) != (range_end - range_start).days + 1:
        fail("Fallback contribution calendar must cover every day in its declared range")


def validate_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lowered = text.casefold()
    for marker in FORBIDDEN_SVG_MARKERS:
        if marker.casefold() in lowered:
            fail(f"{path.name} contains forbidden SVG marker: {marker}")
    if re.search(r"\banimation(?:-[\w-]+)?\s*:|@(?:-\w+-)?keyframes\b|@font-face\b|@import\b", lowered):
        fail(f"{path.name} must remain static and use locally available fonts")
    if re.search(r"url\(\s*['\"]?(?:https?:|//|data:|file:)", lowered):
        fail(f"{path.name} contains an external or embedded CSS asset")
    if "-mobile-" in path.name:
        font_sizes = [float(value) for value in re.findall(r'font-size="(\d+(?:\.\d+)?)"', text)]
        if font_sizes and min(font_sizes) < 11.5:
            fail(f"{path.name} contains mobile SVG type below the 11.5-unit floor")
    if "<title" not in text or "<desc" not in text:
        fail(f"{path.name} lacks accessible title/description metadata")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail(f"{path.name} is not valid XML: {error}")
    if root.tag.rsplit("}", 1)[-1] != "svg":
        fail(f"{path.name} root element is not SVG")
    if root.attrib.get("role") != "img" or not root.attrib.get("viewBox"):
        fail(f"{path.name} lacks image role or viewBox")
    visible_text = " ".join(
        "".join(element.itertext()) for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
    ).casefold()
    if "contributions" not in visible_text:
        fail(f"{path.name} must display GitHub Contributions")
    if not re.search(r"\blast\s+30\s+days\b", visible_text):
        fail(f"{path.name} must label the displayed contribution total as Last 30 days")
    numeric_text = [
        element for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
        and re.fullmatch(r"\d+(?:,\d{3})*", "".join(element.itertext()).strip())
    ]
    if len(numeric_text) != 1:
        fail(f"{path.name} must display exactly one contribution total")
    sparklines = [element for element in root.iter() if element.attrib.get("id") == "contribution-sparkline"]
    if len(sparklines) != 1:
        fail(f"{path.name} must display exactly one contribution sparkline")
    sparkline = sparklines[0]
    if sparkline.tag.rsplit("}", 1)[-1] != "path" or sparkline.attrib.get("fill") != "none":
        fail(f"{path.name} contribution sparkline must be an unfilled path")
    coordinate = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
    point = rf"{coordinate}[\s,]+{coordinate}"
    if not re.fullmatch(rf"\s*M\s*{point}(?:\s*L\s*{point}){{29}}\s*", sparkline.attrib.get("d", "")):
        fail(f"{path.name} contribution sparkline must show exactly thirty daily points")
    rectangles = [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "rect"]
    if len(rectangles) >= 28 or any("data-date" in element.attrib or "data-level" in element.attrib for element in rectangles):
        fail(f"{path.name} must not replace GitHub's native contribution calendar")
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].casefold() in {
            "script", "foreignobject", "animate", "animatetransform", "animatemotion", "set", "mpath",
        }:
            fail(f"{path.name} contains an active or non-static SVG element")
        for attribute, value in element.attrib.items():
            attribute_name = attribute.rsplit("}", 1)[-1].casefold()
            if attribute_name.startswith("on"):
                fail(f"{path.name} contains an event handler")
            if attribute_name in {"href", "src"} and not value.startswith("#"):
                fail(f"{path.name} contains a non-local asset reference")


def validate_workflow() -> None:
    workflow = (ROOT / ".github" / "workflows" / "update-profile.yml").read_text(encoding="utf-8")
    if "contents: write" not in workflow:
        fail("Telemetry workflow requires scoped contents write permission")
    if "pull-requests: write" in workflow or "issues: write" in workflow:
        fail("Telemetry workflow requests unnecessary permissions")
    required_commands = (
        "python -m unittest discover -s tests -v",
        "scripts/generate_profile.py --live",
        "scripts/validate_profile.py",
    )
    if any(command not in workflow for command in required_commands):
        fail("Telemetry workflow must test, generate live assets, and validate them")
    if "GITHUB_TOKEN:" in workflow:
        fail("Public telemetry generation must not receive the repository-scoped GitHub token")
    if "push:" not in workflow or '"tests/**"' not in workflow or '"README.md"' not in workflow:
        fail("Telemetry workflow must verify README and generator changes pushed to main")
    if "[skip ci]" in workflow:
        fail("Telemetry commits must rely on bounded paths instead of a skip-ci marker")
    required_output_controls = (
        "git diff --quiet -- assets/generated config/profile.json",
        "git add assets/generated config/profile.json",
        "git push",
    )
    if any(control not in workflow for control in required_output_controls):
        fail("Telemetry workflow must save verified snapshot data and assets on main, skipping unchanged output")


def relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    bright, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def validate_palette_contrast() -> None:
    for role in ("ink", "muted", "faint", "gold"):
        if contrast_ratio(PALETTE[role], PALETTE["background"]) < 4.5:
            fail(f"Contribution panel {role} text does not reach 4.5:1 against its background")


def validate_repository_boundary() -> None:
    """The scripts and the workflow act on this repository alone."""
    checked = [
        ROOT / "scripts" / "generate_profile.py",
        ROOT / "scripts" / "build_readme.py",
        ROOT / ".github" / "workflows" / "update-profile.yml",
    ]
    for path in checked:
        if SITE_REPOSITORY.casefold() in path.read_text(encoding="utf-8").casefold():
            fail(f"{path.relative_to(ROOT)} reaches outside this repository")


def main() -> None:
    validate_config()
    validate_readme()
    actual = {path.name for path in GENERATED.glob("*.svg")}
    if actual != EXPECTED_ASSETS:
        fail(f"Expected two generated assets, found: {sorted(actual)}")
    for path in sorted(GENERATED.glob("*.svg")):
        validate_svg(path)
    validate_palette_contrast()
    validate_workflow()
    validate_repository_boundary()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    works = sum(len(data["items"]) for data in config["sections"])
    print(f"Profile validation passed: five sections, {works} works with covers, two contribution panels, "
          "contribution data and a scoped workflow.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
