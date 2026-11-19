#!/usr/bin/env python3
"""Build README.md from config/profile.json: a hero, five sections of work, and the contribution panel."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "profile.json"
README = ROOT / "README.md"
RAW = "https://raw.githubusercontent.com/130U/130U/main/assets"
ACTIVITY_MARKER = "<!-- PROFILE_ACTIVITY -->"


def target(item: dict) -> str:
    return item.get("url") or f'https://github.com/130U/{item["repository"]}'


def card(item: dict, width: int) -> str:
    link, title = escape(target(item), quote=True), escape(item["title"])
    return "\n".join([
        f'<td width="{width}%" valign="top">',
        f'<a href="{link}"><img src="assets/covers/{item["cover"]}.webp" alt="{escape(item["title"], quote=True)}" width="100%"></a>',
        f'<p><b><a href="{link}">{title}</a></b><br>{escape(item["line"])}</p>',
        "</td>",
    ])


def section(number: int, data: dict) -> str:
    items = data["items"]
    columns = 3 if len(items) == 3 else 2
    width = 100 // columns
    rows = []
    for index in range(0, len(items), columns):
        cells = [card(item, width) for item in items[index:index + columns]]
        cells.extend([f'<td width="{width}%"></td>'] * (columns - len(cells)))
        rows.append("<tr>\n" + "\n".join(cells) + "\n</tr>")
    return "\n".join([
        f'<a id="{data["id"]}"></a>',
        "",
        f'## {number:02d} &nbsp; {data["title"]}',
        "",
        data["blurb"],
        "",
        "<table>",
        *rows,
        "</table>",
    ])


def build(config: dict) -> str:
    identity = config["identity"]
    sections = config["sections"]
    alt = f'{identity["name"]}. {identity["line"]}'
    navigation = " &nbsp;·&nbsp; ".join(
        f'<a href="#user-content-{data["id"]}">{number:02d} {data["title"]}</a>'
        for number, data in enumerate(sections, start=1)
    )
    parts = [
        "<picture>",
        f'  <source media="(max-width: 767px)" srcset="{RAW}/hero-mobile.webp">',
        f'  <img src="assets/hero.webp" alt="{escape(alt, quote=True)}" width="100%">',
        "</picture>",
        "",
        f'<p align="center">{navigation}</p>',
        "",
    ]
    for number, data in enumerate(sections, start=1):
        parts.extend([section(number, data), ""])
    parts.extend([
        ACTIVITY_MARKER,
        "",
        "<picture>",
        f'  <source media="(max-width: 767px)" srcset="{RAW}/generated/telemetry-mobile-v6.svg">',
        '  <img src="assets/generated/telemetry-v6.svg" alt="GitHub contributions in the last 30 days, with a daily contribution trace." width="100%">',
        "</picture>",
        "",
        "<sub>[Activity updates](https://github.com/130U/130U/actions/workflows/update-profile.yml) · [Data sources](docs/profile-data.md)</sub>",
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
