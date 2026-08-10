#!/usr/bin/env python3
"""Fail closed on repository boundaries, Markdown integrity, and SVG safety."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_profile import PALETTES


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "profile.config.json"
GENERATED = ROOT / "assets" / "generated"
EXPECTED_ASSETS = {
    "hero-light.svg",
    "hero-dark.svg",
    "hero-mobile-light.svg",
    "hero-mobile-dark.svg",
    "telemetry-light.svg",
    "telemetry-dark.svg",
    "telemetry-mobile-light.svg",
    "telemetry-mobile-dark.svg",
    "signals-light.svg",
    "signals-dark.svg",
    "signals-mobile-light.svg",
    "signals-mobile-dark.svg",
}
FORBIDDEN_SCOPE = ("130U.github.io", "theodoreoy.com")
FORBIDDEN_SVG_MARKERS = ("<script", "javascript:", "data:text/html", "vinimlo", "galaxy-profile")
EXPECTED_PROJECT_REPOSITORIES = (
    "bazi-context-agent",
    "info-collector-2026",
    "reserach-portfolio-since2026",
    "agents-last-exam",
)


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_readme() -> None:
    text = README.read_text(encoding="utf-8")
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", text):
        fail("README must remain English-only; CJK characters were found")
    if "assets/generated/hero-light.svg" not in text:
        fail("README is missing the light hero fallback")
    if text.count("/profile-assets/") != 12:
        fail("README must load twelve desktop/mobile theme assets from the isolated profile-assets branch")
    if text.count("<picture>") != 3 or text.count("prefers-color-scheme: dark") != 6:
        fail("README must provide three desktop/mobile theme-aware picture blocks")
    if "Stars" in text or "STARS" in text:
        fail("Low-signal star telemetry must remain omitted")
    if "20 July 2026 at 23:13 Beijing time" not in text:
        fail("README must preserve the stable, human-readable account creation date")
    if "four repositories listed above" not in text:
        fail("README must disclose the selected-repository telemetry scope")
    for forbidden in FORBIDDEN_SCOPE:
        if forbidden.casefold() in text.casefold():
            fail(f"README references forbidden personal-site scope: {forbidden}")


def validate_config() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data["username"] != "130U":
        fail("Profile repository must target exactly 130U")
    if data["account_created_at"] != "2026-07-20T15:13:55Z":
        fail("Authoritative account creation timestamp changed unexpectedly")
    if tuple(data["language_source_repositories"]) != EXPECTED_PROJECT_REPOSITORIES:
        fail("Telemetry must remain confined to the four selected project repositories")
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
    if "prefers-reduced-motion: reduce" not in text:
        fail(f"{path.name} lacks a reduced-motion fallback")
    if "infinite" in lowered:
        fail(f"{path.name} contains perpetual motion without an embedded pause control")
    durations = [float(value) for value in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)s\b", text)]
    if durations and max(durations) > 5:
        fail(f"{path.name} contains motion longer than five seconds")
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
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "script":
            fail(f"{path.name} contains a script element")
        for attribute, value in element.attrib.items():
            if attribute.rsplit("}", 1)[-1] in {"href", "src"} and re.match(r"https?://", value, re.I):
                fail(f"{path.name} contains an external asset reference")


def validate_workflow() -> None:
    workflow = (ROOT / ".github" / "workflows" / "update-profile.yml").read_text(encoding="utf-8")
    if "contents: write" not in workflow:
        fail("Telemetry workflow requires scoped contents write permission")
    if "pull-requests: write" in workflow or "issues: write" in workflow:
        fail("Telemetry workflow requests unnecessary permissions")
    if "scripts/generate_profile.py --live" not in workflow or "scripts/validate_profile.py" not in workflow:
        fail("Telemetry workflow must generate live assets and validate them")
    required_output_controls = (
        "ref: profile-assets",
        "_profile-assets/assets/generated",
        "git diff --quiet",
    )
    if any(control not in workflow for control in required_output_controls):
        fail("Telemetry workflow must isolate generated assets and skip unchanged output")


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
        surface = palette["surface"]
        for role in ("ink", "muted", "faint"):
            if contrast_ratio(palette[role], surface) < 4.5:
                fail(f"{theme} {role} text does not reach 4.5:1 against its surface")
        for role in ("blue", "cyan", "violet", "amber", "green"):
            if contrast_ratio(palette[role], surface) < 3:
                fail(f"{theme} {role} chart mark does not reach 3:1 against its surface")


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
        fail(f"Expected twelve generated assets, found: {sorted(actual)}")
    for path in sorted(GENERATED.glob("*.svg")):
        validate_svg(path)
    validate_palette_contrast()
    validate_workflow()
    validate_repository_boundary()
    print("Profile validation passed: English copy, twelve safe SVGs, scoped workflow, forbidden repositories untouched.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
