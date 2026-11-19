#!/usr/bin/env python3
"""Build README.md from config/profile.json: a hero, five sections of work as a ledger, and the contribution line."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "profile.json"
README = ROOT / "README.md"
RAW = "https://raw.githubusercontent.com/130U/130U/main/assets"
LISTS = "https://github.com/stars/130U/lists"
DATA_NOTE = "docs/profile-data.md"
ACTIVITY_MARKER = "<!-- PROFILE_ACTIVITY -->"
ACTIVITY_ALT = "GitHub contributions in the last 30 days, with a daily contribution trace."
DARK = "(prefers-color-scheme: dark)"

# The page is drawn at three widths, chosen by the width GitHub gives the README at each viewport. Each
# layout lists the viewports that show another layout; there its picture resolves to an empty image, so a
# reader sees one drawing of every line. The hero changes to its tall form where the README is narrowest.
LAYOUTS = (
    ("wide", "(max-width: 1099px)"),
    ("medium", "(max-width: 511px), (min-width: 768px) and (max-width: 789px), (min-width: 1100px)"),
    ("narrow", "(min-width: 512px) and (max-width: 767px), (min-width: 790px)"),
)
HERO_TALL = "(max-width: 601px), (min-width: 768px) and (max-width: 889px)"


def target(item: dict) -> str:
    return item.get("url") or f'https://github.com/130U/{item["repository"]}'


def plain(line: str) -> str:
    """A README lead without its *emphasis* marks."""
    return re.sub(r"\*([^*]+)\*", r"\1", line)


def entry(link: str, folder: str, name: str, alt: str) -> str:
    """One line of the page: a link holding its drawing at each width, light and dark."""
    pictures = []
    for index, (layout, elsewhere) in enumerate(LAYOUTS):
        label = escape(alt, quote=True) if index == 0 else ""
        pictures.append(
            f'<picture><source media="{elsewhere}" srcset="{RAW}/ledger/blank.svg">'
            f'<source media="{DARK}" srcset="{RAW}/{folder}/{layout}-dark/{name}.svg">'
            f'<img src="assets/{folder}/{layout}/{name}.svg" alt="{label}" align="top"></picture>')
    return f'<a href="{escape(link, quote=True)}">' + "".join(pictures) + "</a>"


def section(number: int, data: dict) -> str:
    """A section: its head, linked to the list of the same name, then one line for each work."""
    lines = [entry(f'{LISTS}/{data["id"]}', "ledger", data["id"], f'{number:02d} {data["title"]}. {data["blurb"]}')]
    lines.extend(entry(target(item), "ledger", item["id"], f'{item["title"]}. {plain(item["line"])}')
                 for item in data["items"])
    return "\n".join(["<p>", *lines, "</p>"])


def build(config: dict) -> str:
    identity = config["identity"]
    alt = f'{identity["name"]}. {identity["line"]}'
    parts = [
        "<picture>",
        f'  <source media="{HERO_TALL}" srcset="{RAW}/hero-mobile.webp">',
        f'  <img src="assets/hero.webp" alt="{escape(alt, quote=True)}" width="100%">',
        "</picture>",
        "",
    ]
    for number, data in enumerate(config["sections"], start=1):
        parts.extend([section(number, data), ""])
    parts.extend([
        ACTIVITY_MARKER,
        "",
        "<p>",
        entry(DATA_NOTE, "generated", "contributions", ACTIVITY_ALT),
        "</p>",
        "",
    ])
    return "\n".join(parts)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    README.write_text(build(config), encoding="utf-8", newline="\n")
    works = sum(len(data["items"]) for data in config["sections"])
    print(f'Built README.md: {len(config["sections"])} sections, {works} works.')


if __name__ == "__main__":
    main()
