#!/usr/bin/env python3
"""Fail closed on repository boundaries, Markdown integrity, and SVG safety."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

from generate_profile import PALETTES


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "profile.config.json"
GENERATED = ROOT / "assets" / "generated"
EXPECTED_ASSETS = {
    "hero-light-v3.svg",
    "hero-dark-v3.svg",
    "hero-mobile-light-v3.svg",
    "hero-mobile-dark-v3.svg",
    "telemetry-light-v4.svg",
    "telemetry-dark-v4.svg",
    "telemetry-mobile-light-v4.svg",
    "telemetry-mobile-dark-v4.svg",
}
FORBIDDEN_SCOPE = ("130U.github.io", "theodoreoy.com")
FORBIDDEN_SVG_MARKERS = ("<script", "javascript:", "data:text/html", "vinimlo", "galaxy-profile")
RETIRED_METRIC_LABELS = (
    "engineering commits", "project commits", "pull requests", "public repositories", "public repos",
)
EXPECTED_ACADEMIC_REPOSITORIES = (
    "certified-valuation-arithmetic-asian-options",
    "certified-rough-heston-valuation",
)
EXPECTED_ENGINEERING_DISPLAY_ORDER = (
    "agent-evaluation-methodology",
    "reserach-portfolio-since2026",
    "bazi-context-agent",
    "info-collector-2026",
)


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_readme() -> None:
    text = README.read_text(encoding="utf-8")
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", text):
        fail("README must remain English-only; CJK characters were found")
    if "assets/generated/hero-light-v3.svg" not in text:
        fail("README is missing the light hero fallback")
    references = re.findall(r"/main/assets/generated/([\w-]+\.svg)", text)
    if len(references) != 8 or set(references) != EXPECTED_ASSETS:
        fail("README must load exactly eight desktop/mobile theme assets from main")
    if "/profile-assets/" in text:
        fail("README must not depend on the retired profile-assets branch")
    if text.count("<picture>") != 2 or text.count("prefers-color-scheme: dark") != 4:
        fail("README must provide two desktop/mobile theme-aware picture blocks")
    if text.count("(max-width: 767px)") != 4 or "(max-width: 600px)" in text:
        fail("README must use the tested 767px mobile asset breakpoint")
    if '#artificial-intelligence-and-engineering' not in text:
        fail("README must link its main navigation to Artificial Intelligence and Engineering")
    if "Stars" in text or "STARS" in text:
        fail("Low-signal star telemetry must remain omitted")
    retired_copy = (
        "How the live clock works", "account age", "selected systems",
        "#selected-systems", "evidence before spectacle", "current questions",
        "Engineering & Applied AI", "GitHub Activity", *RETIRED_METRIC_LABELS,
    )
    if any(marker.casefold() in text.casefold() for marker in retired_copy):
        fail("README contains retired clock or profile positioning copy")
    headings = ("Artificial Intelligence and Engineering", "Mathematical Finance", "GitHub Contributions")
    heading_matches = [re.search(rf"^## {re.escape(heading)}\s*$", text, re.M) for heading in headings]
    if any(match is None for match in heading_matches):
        fail("README is missing a required AI, mathematical finance, or contribution section")
    positions = [match.start() for match in heading_matches if match is not None]
    if positions != sorted(positions):
        fail("README must lead with AI and engineering, then mathematical finance, then contributions")
    engineering = text[positions[0]:positions[1]]
    academic = text[positions[1]:positions[2]]
    for section, repositories in (
        (academic, EXPECTED_ACADEMIC_REPOSITORIES),
        (engineering, EXPECTED_ENGINEERING_DISPLAY_ORDER),
    ):
        links = [f"https://github.com/130U/{repository}" for repository in repositories]
        if any(link not in section for link in links):
            fail("README is missing a required project in its designated section")
        link_positions = [section.index(link) for link in links]
        if link_positions != sorted(link_positions):
            fail("README project ordering changed unexpectedly")
    contributions = text[positions[2]:]
    if len(re.findall(r"^## ", contributions, re.M)) != 1:
        fail("GitHub Contributions must remain the final major README section")
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
    validate_palette_contrast()
    validate_workflow()
    validate_repository_boundary()
    print("Profile validation passed: AI-first English copy, eight static safe SVGs, contribution data, scoped workflow, forbidden repositories untouched.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
