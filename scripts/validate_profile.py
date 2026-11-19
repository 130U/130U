#!/usr/bin/env python3
"""Validate the profile: the README equals its build, every line of the ledger has its drawings, and the contribution line is sound."""

from __future__ import annotations

import calendar
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_readme  # noqa: E402
from generate_profile import LAYOUTS, MEASURE, PANEL, THEMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "config" / "profile.json"
TYPE = ROOT / "config" / "type.json"
ASSETS = ROOT / "assets"
GENERATED = ASSETS / "generated"
LEDGER = ASSETS / "ledger"
FOLDERS = tuple(folder for layout, _ in build_readme.LAYOUTS for folder in (layout, f"{layout}-dark"))
HERO_ASSETS = ("hero.webp", "hero-mobile.webp")
EXPECTED_SECTIONS = ("research", "engineering", "law", "blog", "me")
SITE_REPOSITORY = "130U.github.io"
FORBIDDEN_SVG_MARKERS = ("<script", "javascript:", "data:text/html")
ACTIVE_SVG_ELEMENTS = {"script", "foreignobject", "animate", "animatetransform", "animatemotion", "set", "mpath"}
STAMP = re.compile(r"(Updated|Saved snapshot) \d{2} [A-Z][a-z]{2} \d{4} UTC")


def fail(message: str) -> None:
    raise AssertionError(message)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class ReadmeLinks(HTMLParser):
    """Collect each link of the README with the pictures it holds, in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict] = []
        self.loose_images: list[tuple[str, str]] = []
        self.sources: list[str] = []
        self.current: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.current = {"href": attributes["href"], "images": []}
            self.links.append(self.current)
        elif tag == "img":
            image = (attributes.get("src", ""), attributes.get("alt", ""))
            (self.current["images"] if self.current else self.loose_images).append(image)
        elif tag == "source":
            self.sources.append(attributes.get("srcset", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.current = None


def ledger_titles(config: dict) -> dict[str, str]:
    """The text every drawing of the ledger carries, by file name."""
    titles: dict[str, str] = {}
    for number, data in enumerate(config["sections"], start=1):
        titles[data["id"]] = f'{number:02d} {data["title"]}. {data["blurb"]}'
        for item in data["items"]:
            titles[item["id"]] = f'{item["title"]}. {build_readme.plain(item["line"])}'
    return titles


def validate_sections(config: dict) -> None:
    identity = config.get("identity", {})
    if not identity.get("name") or not identity.get("line"):
        fail("Configuration must name the author and give the positioning line")
    sections = config.get("sections")
    if not isinstance(sections, list) or tuple(data.get("id") for data in sections) != EXPECTED_SECTIONS:
        fail("Configuration must list the five sections in order: " + ", ".join(EXPECTED_SECTIONS))
    seen_repositories: set[str] = set()
    seen_ids: set[str] = set(EXPECTED_SECTIONS)
    for data in sections:
        if not data.get("title") or not data.get("blurb") or not data.get("items"):
            fail(f'Section {data["id"]} needs a title, a blurb and at least one work')
        for item in data["items"]:
            for field in ("repository", "title", "line", "id"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    fail(f'A work in {data["id"]} lacks its {field}')
            if item["repository"] in seen_repositories or item["id"] in seen_ids:
                fail(f'{item["repository"]} or its id appears twice')
            seen_repositories.add(item["repository"])
            seen_ids.add(item["id"])
            if not re.fullmatch(r"[A-Za-z0-9._-]+", item["repository"]) or not re.fullmatch(r"[a-z0-9-]+", item["id"]):
                fail(f'{item["repository"]} has an invalid repository or id')
            if "url" in item and item["repository"] != SITE_REPOSITORY:
                fail("Only the personal website may link outside its repository")


def validate_static_svg(path: Path) -> ET.Element:
    """An image of this page is static, self-contained and named for readers who cannot see it."""
    text = path.read_text(encoding="utf-8")
    lowered = text.casefold()
    for marker in FORBIDDEN_SVG_MARKERS:
        if marker.casefold() in lowered:
            fail(f"{path.name} contains forbidden SVG marker: {marker}")
    if re.search(r"\banimation(?:-[\w-]+)?\s*:|@(?:-\w+-)?keyframes\b|@font-face\b|@import\b", lowered):
        fail(f"{path.name} must remain static and carry its own letterforms")
    if re.search(r"url\(\s*['\"]?(?:https?:|//|data:|file:)", lowered):
        fail(f"{path.name} contains an external or embedded CSS asset")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail(f"{path.name} is not valid XML: {error}")
    if local_name(root.tag) != "svg":
        fail(f"{path.name} root element is not SVG")
    if root.attrib.get("role") != "img" or not root.attrib.get("viewBox"):
        fail(f"{path.name} lacks image role or viewBox")
    if not any(local_name(element.tag) == "title" and (element.text or "").strip() for element in root):
        fail(f"{path.name} lacks an accessible title")
    outlines = {element.attrib["id"] for element in root.iter() if "id" in element.attrib}
    for element in root.iter():
        name = local_name(element.tag).casefold()
        if name in ACTIVE_SVG_ELEMENTS:
            fail(f"{path.name} contains an active or non-static SVG element")
        if name == "text":
            fail(f"{path.name} must draw its type as outlines")
        for attribute, value in element.attrib.items():
            attribute_name = local_name(attribute).casefold()
            if attribute_name.startswith("on"):
                fail(f"{path.name} contains an event handler")
            if attribute_name in {"href", "src"} and (not value.startswith("#") or value[1:] not in outlines):
                fail(f"{path.name} contains a non-local asset reference")
    return root


def validate_ledger(config: dict) -> None:
    titles = ledger_titles(config)
    expected = {f"{name}.svg" for name in titles}
    if not (LEDGER / "blank.svg").is_file():
        fail("Missing the empty image assets/ledger/blank.svg")
    if {path.name for path in LEDGER.iterdir()} != {*FOLDERS, "blank.svg"}:
        fail("assets/ledger must hold one folder for each layout and theme, and blank.svg")
    for folder in FOLDERS:
        on_disk = {path.name for path in (LEDGER / folder).iterdir()}
        if on_disk != expected:
            fail(f"Ledger drawings in {folder} and listed works differ: {sorted(on_disk ^ expected)}")
        for name, title in titles.items():
            root = validate_static_svg(LEDGER / folder / f"{name}.svg")
            drawn = next(element.text for element in root if local_name(element.tag) == "title")
            if drawn != title:
                fail(f"assets/ledger/{folder}/{name}.svg was drawn from other text than the configuration holds")


def validate_readme() -> None:
    text = README.read_text(encoding="utf-8")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if re.search(r"[㐀-鿿豈-﫿]", text):
        fail("README must remain English-only; CJK characters were found")
    if text != build_readme.build(config):
        fail("README.md differs from its build; run scripts/build_readme.py")
    parser = ReadmeLinks()
    parser.feed(text)
    parser.close()
    if text.count(build_readme.ACTIVITY_MARKER) != 1 or text.index(build_readme.ACTIVITY_MARKER) < text.rindex(
            f'{build_readme.LISTS}/{EXPECTED_SECTIONS[-1]}'):
        fail("README must place one contribution line after the last section")
    expected_links = []
    for data in config["sections"]:
        expected_links.append(f'{build_readme.LISTS}/{data["id"]}')
        expected_links.extend(build_readme.target(item) for item in data["items"])
    expected_links.append(build_readme.DATA_NOTE)
    if [link["href"] for link in parser.links] != expected_links:
        fail("README work ordering or link destination differs from the configuration")
    for link in parser.links:
        labels = [alt for _, alt in link["images"]]
        if len(labels) != len(build_readme.LAYOUTS) or not labels[0] or any(labels[1:]):
            fail(f'{link["href"]} must hold one drawing per layout and name itself once')
    if len(parser.loose_images) != 1 or not parser.loose_images[0][1]:
        fail("README must open with one hero image that has alternative text")
    images = parser.loose_images + [image for link in parser.links for image in link["images"]]
    for source, _ in images:
        if not source.startswith("assets/") or not (ROOT / source).is_file():
            fail(f"README image is not a local asset: {source}")
    for source in parser.sources:
        if not source.startswith(build_readme.RAW + "/") or not (ASSETS / source[len(build_readme.RAW) + 1:]).is_file():
            fail(f"README picture source is not an asset of this repository: {source}")
    for name in HERO_ASSETS:
        if not (ASSETS / name).is_file():
            fail(f"Missing hero image assets/{name}")


def validate_config() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data["username"] != "130U":
        fail("Profile repository must target exactly 130U")
    validate_sections(data)
    validate_ledger(data)
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


def validate_type() -> None:
    """The letter table holds every character the contribution line can set."""
    face = json.loads(TYPE.read_text(encoding="utf-8"))
    needed = set("0123456789, " + MEASURE + "Updated" + "Saved snapshot" + "UTC" + "".join(calendar.month_abbr))
    missing = sorted(needed - set(face.get("glyphs", {})))
    if missing:
        fail(f"config/type.json lacks the letters {missing}")
    if type(face.get("units_per_em")) is not int or face["units_per_em"] <= 0:
        fail("config/type.json must state its units per em")
    for character, (advance, outline) in face["glyphs"].items():
        if type(advance) is not int or advance <= 0 or not isinstance(outline, str):
            fail(f"config/type.json holds an invalid letter: {character!r}")
        if not re.fullmatch(r"[MLHVQCZ0-9 .-]*", outline):
            fail(f"config/type.json holds an outline that is more than a path: {character!r}")
    for pair, shift in face.get("kerning", {}).items():
        if len(pair) != 2 or set(pair) - set(face["glyphs"]) or type(shift) is not int:
            fail(f"config/type.json holds an invalid kerning pair: {pair!r}")


def validate_svg(path: Path) -> None:
    """A drawing of the contribution line: one total, its measure, its date and thirty daily points."""
    root = validate_static_svg(path)
    description = next((element.text or "" for element in root if local_name(element.tag) == "desc"), "")
    drawn = [element.attrib["data-text"] for element in root.iter() if "data-text" in element.attrib]
    totals = [value for value in drawn if re.fullmatch(r"\d+(?:,\d{3})*", value)]
    if len(totals) != 1:
        fail(f"{path.name} must display exactly one contribution total")
    if MEASURE not in drawn or not re.search(r"\blast\s+30\s+days\b", MEASURE):
        fail(f"{path.name} must label the displayed contribution total as the last 30 days")
    stamps = [value for value in drawn if STAMP.fullmatch(value)]
    if len(stamps) != 1 or len(drawn) != 3:
        fail(f"{path.name} must date its data once and draw nothing else in type")
    if not description.startswith(f"{totals[0]} GitHub contributions in the last 30 days") or stamps[0] not in description:
        fail(f"{path.name} must describe the total and the date it displays")
    sparklines = [element for element in root.iter() if element.attrib.get("id") == "contribution-sparkline"]
    if len(sparklines) != 1:
        fail(f"{path.name} must display exactly one contribution sparkline")
    sparkline = sparklines[0]
    if local_name(sparkline.tag) != "path" or sparkline.attrib.get("fill") != "none":
        fail(f"{path.name} contribution sparkline must be an unfilled path")
    coordinate = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
    point = rf"{coordinate}[\s,]+{coordinate}"
    if not re.fullmatch(rf"\s*M\s*{point}(?:\s*L\s*{point}){{29}}\s*", sparkline.attrib.get("d", "")):
        fail(f"{path.name} contribution sparkline must show exactly thirty daily points")
    rectangles = [element for element in root.iter() if local_name(element.tag) == "rect"]
    if len(rectangles) >= 28 or any("data-date" in element.attrib or "data-level" in element.attrib for element in root.iter()):
        fail(f"{path.name} must not replace GitHub's native contribution calendar")


def validate_generated() -> None:
    if {path.name for path in GENERATED.iterdir()} != set(FOLDERS):
        fail("assets/generated must hold one folder for each layout and theme")
    for folder in FOLDERS:
        if {path.name for path in (GENERATED / folder).iterdir()} != {PANEL}:
            fail(f"assets/generated/{folder} must hold exactly {PANEL}")
        validate_svg(GENERATED / folder / PANEL)
    if set(LAYOUTS) != {layout for layout, _ in build_readme.LAYOUTS}:
        fail("The contribution line and the README must share their layouts")


def validate_workflow() -> None:
    workflow = (ROOT / ".github" / "workflows" / "update-profile.yml").read_text(encoding="utf-8")
    if "contents: write" not in workflow:
        fail("Contribution workflow requires scoped contents write permission")
    if "pull-requests: write" in workflow or "issues: write" in workflow:
        fail("Contribution workflow requests unnecessary permissions")
    if re.search(r"uses:\s*[\w.-]+/[\w.-]+@(?![0-9a-f]{40}\b)", workflow):
        fail("Contribution workflow must pin every action to a full commit SHA")
    required_commands = (
        "python -m unittest discover -s tests -v",
        "scripts/generate_profile.py --live",
        "scripts/validate_profile.py",
    )
    if any(command not in workflow for command in required_commands):
        fail("Contribution workflow must test, generate live assets, and validate them")
    if "GITHUB_TOKEN:" in workflow:
        fail("Public contribution generation must not receive the repository-scoped GitHub token")
    if "push:" not in workflow or '"tests/**"' not in workflow or '"README.md"' not in workflow:
        fail("Contribution workflow must verify README and generator changes pushed to main")
    if '"config/**"' not in workflow or '"assets/ledger/**"' not in workflow:
        fail("Contribution workflow must verify configuration and ledger changes pushed to main")
    if "[skip ci]" in workflow:
        fail("Contribution commits must rely on bounded paths instead of a skip-ci marker")
    required_output_controls = (
        "git diff --quiet -- assets/generated config/profile.json",
        "git add assets/generated config/profile.json",
        "git push",
    )
    if any(control not in workflow for control in required_output_controls):
        fail("Contribution workflow must save verified snapshot data and assets on main, skipping unchanged output")


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
    for name, theme in THEMES.items():
        for role in ("ink", "muted"):
            if contrast_ratio(theme[role], theme["page"]) < 4.5:
                fail(f"Contribution line {role} text does not reach 4.5:1 on the {name} page")
        if contrast_ratio(theme["accent"], theme["page"]) < 3:
            fail(f"Contribution line accent does not reach 3:1 on the {name} page")


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
    validate_type()
    validate_generated()
    validate_palette_contrast()
    validate_workflow()
    validate_repository_boundary()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    works = sum(len(data["items"]) for data in config["sections"])
    print(f"Profile validation passed: five sections, {works} works drawn at {len(build_readme.LAYOUTS)} widths "
          "in two themes, the contribution line, its data and a scoped workflow.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
