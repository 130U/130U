#!/usr/bin/env python3
"""Fail closed on repository boundaries, Markdown integrity, and SVG safety."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

from generate_profile import PALETTES, TELEMETRY_PALETTES


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "profile.config.json"
GENERATED = ROOT / "assets" / "generated"
LAYOUT = ROOT / "assets" / "layout"
EXPECTED_ASSETS = {
    "hero-light-v5.svg",
    "hero-dark-v5.svg",
    "hero-mobile-light-v5.svg",
    "hero-mobile-dark-v5.svg",
    "telemetry-light-v5.svg",
    "telemetry-dark-v5.svg",
    "telemetry-mobile-light-v5.svg",
    "telemetry-mobile-dark-v5.svg",
}
EXPECTED_LAYOUT_BUTTONS = {
    f"{name}-v2.svg" for name in (
        "button-paper", "button-repository", "button-results", "button-model",
        "button-training", "button-analysis", "nav-ai", "nav-finance",
    )
}
EXPECTED_LAYOUT_ASSETS = EXPECTED_LAYOUT_BUTTONS | {
    f"sheet-{section}-{variant}-v2.svg"
    for section in ("ai", "finance")
    for variant in ("light", "dark", "mobile-light", "mobile-dark")
}
FORBIDDEN_SCOPE = ("130U.github.io", "theodoreoy.com")
FORBIDDEN_SVG_MARKERS = ("<script", "javascript:", "data:text/html", "vinimlo", "galaxy-profile")
RETIRED_METRIC_LABELS = (
    "engineering commits", "project commits", "pull requests", "public repositories", "public repos",
)
EXPECTED_ACADEMIC_REPOSITORIES = (
    "certified-valuation-arithmetic-asian-options",
    "certified-rough-heston-valuation",
    "mathematical-finance-project",
)
EXPECTED_ENGINEERING_DISPLAY_ORDER = (
    "agent-evaluation-methodology",
    "130U-FinLLM",
    "reserach-portfolio-since2026",
    "bazi-context-agent",
    "info-collector-2026",
)


def fail(message: str) -> None:
    raise AssertionError(message)


@dataclass
class ReadmeElement:
    tag: str
    attrs: dict[str, str | None]
    start: int
    parent: ReadmeElement | None
    end: int = 0


class ReadmeParser(HTMLParser):
    """Read the authored HTML without guessing structure from Markdown regexes."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.line_offsets = [0]
        for match in re.finditer("\n", source):
            self.line_offsets.append(match.end())
        self.elements: list[ReadmeElement] = []
        self.stack: list[ReadmeElement] = []

    def absolute_offset(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = ReadmeElement(tag, dict(attrs), self.absolute_offset(), self.stack[-1] if self.stack else None)
        self.elements.append(element)
        if tag in self.VOID_TAGS:
            element.end = element.start + len(self.get_starttag_text())
        else:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID_TAGS:
            fail(f"README must not close the void HTML element {tag}")
        if not self.stack or self.stack[-1].tag != tag:
            fail(f"README contains unbalanced HTML at </{tag}>")
        self.stack.pop().end = self.absolute_offset() + len(tag) + 3

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.stack.pop().end = self.absolute_offset() + len(self.get_starttag_text())


def is_within(element: ReadmeElement, container: ReadmeElement) -> bool:
    parent = element.parent
    while parent is not None:
        if parent is container:
            return True
        parent = parent.parent
    return False


def validate_picture(picture: ReadmeElement, elements: list[ReadmeElement],
                     directory: str, stem: str, version: str) -> None:
    sources = [element for element in elements if element.tag == "source" and element.parent is picture]
    if directory == "layout":
        variants = [
            ("(prefers-color-scheme: dark) and (max-width: 767px)", "mobile-dark"),
            ("(max-width: 767px)", "mobile-light"),
            ("(prefers-color-scheme: dark)", "dark"),
        ]
    else:
        variants = [
            (f"(max-width: 767px) and (prefers-color-scheme: {theme})", f"mobile-{theme}")
            for theme in ("dark", "light")
        ] + [(f"(prefers-color-scheme: {theme})", theme) for theme in ("dark", "light")]
    expected = [(media, f"https://raw.githubusercontent.com/130U/130U/main/assets/{directory}/{stem}-{variant}-{version}.svg")
                for media, variant in variants]
    actual = [(source.attrs.get("media"), source.attrs.get("srcset")) for source in sources]
    if actual != expected:
        fail(f"README {stem} picture must provide ordered desktop/mobile theme sources from main at the 767px breakpoint")
    images = [element for element in elements if element.tag == "img" and element.parent is picture]
    fallback = f"assets/{directory}/{stem}-light-{version}.svg"
    if len(images) != 1 or images[0].attrs.get("src") != fallback or not images[0].attrs.get("alt"):
        fail(f"README {stem} picture must provide its local light fallback and accessible alt text")


def validate_readme() -> None:
    text = README.read_text(encoding="utf-8")
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", text):
        fail("README must remain English-only; CJK characters were found")
    references = re.findall(r"/main/assets/generated/([\w-]+\.svg)", text)
    if len(references) != 8 or set(references) != EXPECTED_ASSETS:
        fail("README must load exactly eight desktop/mobile theme assets from main")
    if "/profile-assets/" in text:
        fail("README must not depend on the retired profile-assets branch")
    if "Stars" in text or "STARS" in text:
        fail("Low-signal star telemetry must remain omitted")
    retired_copy = (
        "How the live clock works", "account age", "selected systems",
        "#selected-systems", "evidence before spectacle", "current questions",
        "Engineering & Applied AI", "GitHub Activity", *RETIRED_METRIC_LABELS,
    )
    if any(marker.casefold() in text.casefold() for marker in retired_copy):
        fail("README contains retired clock or profile positioning copy")
    parser = ReadmeParser(text)
    parser.feed(text)
    parser.close()
    if parser.stack:
        fail("README contains unclosed HTML elements")
    elements = parser.elements
    tables = [element for element in elements if element.tag == "table"]
    pictures = [element for element in elements if element.tag == "picture"]
    headings = [element for element in elements if element.tag == "h3"]
    if len(tables) != 2 or any(is_within(table, other) for table in tables for other in tables if table is not other):
        fail("README must contain exactly two nonnested project sheets: AI Engineering, then Finance")
    if len(pictures) != 4:
        fail("README must provide hero, two sheet headers, and activity picture blocks")
    if re.search(r"^#{2,3} ", text, re.M) or any(element.tag == "h2" for element in elements):
        fail("README section headers must live in the two sheets, with native HTML project headings")
    if len(headings) != 8 or any(not any(is_within(heading, table) for table in tables) for heading in headings):
        fail("README must retain five AI and three Finance project headings inside the sheets")
    activity_marker = "<!-- PROFILE_ACTIVITY -->"
    if text.count(activity_marker) != 1 or text.index(activity_marker) <= tables[1].end:
        fail("README must place one activity footer after the Finance projects")
    activity_position = text.index(activity_marker)
    if pictures[0].end >= tables[0].start or pictures[-1].start <= activity_position:
        fail("README hero must precede the sheets and activity must remain a separate footer")
    validate_picture(pictures[0], elements, "generated", "hero", "v5")
    validate_picture(pictures[-1], elements, "generated", "telemetry", "v5")
    buttons = []
    allowed_images = {f"assets/generated/{name}" for name in EXPECTED_ASSETS} | {
        f"assets/layout/{name}" for name in EXPECTED_LAYOUT_ASSETS
    }
    for image in (element for element in elements if element.tag == "img"):
        source = image.attrs.get("src", "")
        if source not in allowed_images or not image.attrs.get("alt"):
            fail("README images must use approved local assets and accessible alt text")
        if source.removeprefix("assets/layout/") in EXPECTED_LAYOUT_BUTTONS:
            if image.parent is None or image.parent.tag != "a" or not image.parent.attrs.get("href"):
                fail("README buttons must be images inside working links")
            buttons.append(image)
        elif image.parent is None or image.parent.tag != "picture":
            fail("README theme-aware image fallbacks must remain inside their picture blocks")
    for index, (table, anchor, stem, repositories) in enumerate(zip(
        tables, ("ai-engineering", "finance"), ("sheet-ai", "sheet-finance"),
        (EXPECTED_ENGINEERING_DISPLAY_ORDER, EXPECTED_ACADEMIC_REPOSITORIES),
    )):
        descendants = [element for element in elements if is_within(element, table)]
        rows = [element for element in descendants if element.tag == "tr"]
        cells = [element for element in descendants if element.tag == "td"]
        if len(rows) != 1 or len(cells) != 1 or cells[0].parent is not rows[0] or any(element.tag == "th" for element in descendants):
            fail("Each README sheet must contain exactly one table row and one cell")
        anchors = [element for element in elements if element.tag == "a" and element.attrs.get("id") == anchor]
        lower_bound = tables[index - 1].end if index else pictures[0].end
        if len(anchors) != 1 or not lower_bound <= anchors[0].start < anchors[0].end <= table.start:
            fail(f"README requires a unique {anchor} anchor before its sheet")
        header_pictures = [element for element in descendants if element.tag == "picture"]
        project_headings = [element for element in descendants if element.tag == "h3"]
        if len(header_pictures) != 1 or len(project_headings) != len(repositories):
            fail("README must give every project its own third-level heading below its sheet header")
        if any(not is_within(heading, cells[0]) for heading in project_headings):
            fail("README project headings must remain inside their sheet's single cell")
        if header_pictures[0].end >= project_headings[0].start or not is_within(header_pictures[0], cells[0]):
            fail("README sheet header must begin its single cell before the projects")
        validate_picture(header_pictures[0], elements, "layout", stem, "v2")
        for project_index, repository in enumerate(repositories):
            heading = project_headings[project_index]
            end = project_headings[project_index + 1].start if project_index + 1 < len(project_headings) else table.end
            project_buttons = [button for button in buttons if heading.end <= button.start < end]
            if not project_buttons:
                fail("README is missing a project link button in its designated section")
            link = f"https://github.com/130U/{repository}"
            for button in project_buttons:
                target = button.parent.attrs["href"]
                if target != link and not target.startswith(link + "/"):
                    fail("README project ordering or button destination changed unexpectedly")
    for asset, anchor in (("nav-ai-v2.svg", "#user-content-ai-engineering"), ("nav-finance-v2.svg", "#user-content-finance")):
        navigation = [button for button in buttons if button.attrs["src"] == f"assets/layout/{asset}"]
        if len(navigation) != 1 or navigation[0].parent.attrs.get("href") != anchor or navigation[0].start >= tables[0].start:
            fail("README navigation buttons must link once to each sheet before the projects")
    for forbidden in FORBIDDEN_SCOPE:
        if forbidden.casefold() in text.casefold():
            fail(f"README references forbidden personal-site scope: {forbidden}")


def validate_config() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data["username"] != "130U":
        fail("Profile repository must target exactly 130U")
    snapshot_at = data.get("snapshot_updated_at")
    try:
        snapshot = datetime.fromisoformat(snapshot_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        fail("Fallback metrics require a valid snapshot_updated_at timestamp")
    if snapshot.tzinfo is None or snapshot.utcoffset() is None:
        fail("Fallback snapshot_updated_at must identify its timezone")
    if snapshot > datetime.now(snapshot.tzinfo):
        fail("Fallback snapshot_updated_at must not claim a future data collection time")
    retired_fields = (
        "language_source_repositories", "account_created_at", "fallback_languages", "fallback_metrics",
    )
    if any(field in data for field in retired_fields):
        fail("Configuration must not retain repository-scoped telemetry or account-age fields")
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
    serialized = json.dumps(data, ensure_ascii=False)
    for forbidden in FORBIDDEN_SCOPE:
        if forbidden.casefold() in serialized.casefold():
            fail(f"Configuration crosses forbidden repository scope: {forbidden}")


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
    forbidden_markers = ("seconds-frame", "seconds-hand", "account age", "chronograph", "orbiter-", "bar-scan", "research-sweep")
    if any(marker in lowered for marker in forbidden_markers):
        fail(f"{path.name} contains retired clock or signal content")
    if any(marker in lowered for marker in RETIRED_METRIC_LABELS):
        fail(f"{path.name} contains a retired repository-scoped telemetry metric")
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
    if path.name.startswith("telemetry-"):
        if "contributions" not in " ".join(root.itertext()).casefold():
            fail(f"{path.name} must display GitHub Contributions")
        visible_text = " ".join(
            "".join(element.itertext()) for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "text"
        ).casefold()
        if not re.search(r"\blast\s+30\s+days\b", visible_text):
            fail(f"{path.name} must label the displayed contribution total as Last 30 days")
        if re.search(r"\blast\s+year\b", visible_text):
            fail(f"{path.name} must not display the retired annual contribution period")
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
        if len(rectangles) >= 28 or any(
            "data-date" in element.attrib or "data-level" in element.attrib
            for element in rectangles
        ):
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
        "git diff --quiet -- assets/generated profile.config.json",
        "git add assets/generated profile.config.json",
        "git push",
    )
    if any(control not in workflow for control in required_output_controls):
        fail("Telemetry workflow must save verified snapshot data and assets on main, skipping unchanged output")
    if "profile-assets" in workflow or "_profile-assets" in workflow:
        fail("Telemetry workflow must not depend on the retired asset branch")


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
    for theme, palette in TELEMETRY_PALETTES.items():
        for role in ("number", "title", "description", "timestamp"):
            if contrast_ratio(palette[role], palette["background"]) < 4.5:
                fail(f"{theme} contribution {role} text does not reach 4.5:1 against its background")
    for theme, palette in PALETTES.items():
        backgrounds = ("bg_a", "bg_b", "surface", "surface_2")
        for role in ("ink", "muted", "faint"):
            for background in backgrounds:
                if contrast_ratio(palette[role], palette[background]) < 4.5:
                    fail(f"{theme} {role} text does not reach 4.5:1 against {background}")
        for background in backgrounds:
            if contrast_ratio(palette["blue"], palette[background]) < 3:
                fail(f"{theme} blue accent does not reach 3:1 against {background}")
        for path in GENERATED.glob(f"*-{theme}-v*.svg"):
            root = ET.parse(path).getroot()
            blue_text = any(
                element.tag.rsplit("}", 1)[-1] == "text"
                and element.attrib.get("fill", "").casefold() == palette["blue"].casefold()
                for element in root.iter()
            )
            if blue_text:
                for background in backgrounds:
                    if contrast_ratio(palette["blue"], palette[background]) < 4.5:
                        fail(f"{theme} blue text does not reach 4.5:1 against {background}")


def validate_repository_boundary() -> None:
    checked = [
        README,
        CONFIG,
        ROOT / "scripts" / "generate_profile.py",
        ROOT / "scripts" / "validate_profile.py",
        ROOT / ".github" / "workflows" / "update-profile.yml",
    ]
    for path in checked:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_SCOPE:
            if forbidden.casefold() in text.casefold() and path.name != "validate_profile.py":
                fail(f"{path.relative_to(ROOT)} references forbidden scope: {forbidden}")


def main() -> None:
    validate_readme()
    validate_config()
    actual = {path.name for path in GENERATED.glob("*.svg")}
    if actual != EXPECTED_ASSETS:
        fail(f"Expected eight generated assets, found: {sorted(actual)}")
    for path in sorted(GENERATED.glob("*.svg")):
        validate_svg(path)
    layout_assets = {path.name for path in LAYOUT.glob("*.svg")}
    if layout_assets != EXPECTED_LAYOUT_ASSETS:
        fail(f"Expected sixteen static layout assets, found: {sorted(layout_assets)}")
    for path in sorted(LAYOUT.glob("*.svg")):
        validate_svg(path)
    validate_palette_contrast()
    validate_workflow()
    validate_repository_boundary()
    print("Profile validation passed: two project sheets, eight generated and sixteen layout SVGs, contribution data, scoped workflow, forbidden repositories untouched.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
