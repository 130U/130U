#!/usr/bin/env python3
"""Generate original, self-contained SVG assets for the 130U Profile README."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "profile.config.json"
OUTPUT_DIR = ROOT / "assets" / "generated"
API_ROOT = "https://api.github.com"


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


def api_get(path: str) -> object:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "130U-profile-generator",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def api_get_all(path: str, per_page: int = 100, max_pages: int = 50) -> list[dict]:
    """Collect a small public repository listing without using GitHub Search."""
    items: list[dict] = []
    separator = "&" if "?" in path else "?"
    for page in range(1, max_pages + 1):
        batch = api_get(f"{path}{separator}{urllib.parse.urlencode({'per_page': per_page, 'page': page})}")
        if not isinstance(batch, list):
            raise RuntimeError(f"Expected a GitHub list response for {path}")
        items.extend(batch)
        if len(batch) < per_page:
            return items
    raise RuntimeError(f"GitHub listing exceeded {max_pages} pages for {path}")


def collect_live_data(config: dict) -> dict:
    username = config["username"]
    encoded_username = urllib.parse.quote(username)
    user = api_get(f"/users/{encoded_username}")

    language_bytes: dict[str, int] = {}
    project_commits = 0
    project_pull_requests = 0
    for repository in config["language_source_repositories"]:
        repository_root = f"/repos/{encoded_username}/{urllib.parse.quote(repository)}"
        commit_query = urllib.parse.urlencode({"author": username})
        project_commits += len(api_get_all(f"{repository_root}/commits?{commit_query}"))

        pull_requests = api_get_all(f"{repository_root}/pulls?state=all")
        project_pull_requests += sum(
            1
            for pull_request in pull_requests
            if (pull_request.get("user") or {}).get("login", "").casefold() == username.casefold()
        )

        for language, size in api_get(f"{repository_root}/languages").items():
            language_bytes[language] = language_bytes.get(language, 0) + int(size)

    return {
        "created_at": user["created_at"],
        "public_commits": project_commits,
        "pull_requests": project_pull_requests,
        "public_repositories": int(user["public_repos"]),
        "languages": language_bytes,
        "source": "GitHub public API",
    }


def collect_snapshot_data(config: dict) -> dict:
    metrics = config["fallback_metrics"]
    return {
        "created_at": config["account_created_at"],
        "public_commits": int(metrics["public_commits"]),
        "pull_requests": int(metrics["pull_requests"]),
        "public_repositories": int(metrics["public_repositories"]),
        "languages": config["fallback_languages"],
        "source": "verified local snapshot",
        "snapshot_at": config.get("snapshot_updated_at"),
    }


def resolve_profile_data(config: dict, live: bool) -> dict:
    if not live:
        return collect_snapshot_data(config)
    try:
        return collect_live_data(config)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        if isinstance(error, urllib.error.HTTPError):
            reason = f"HTTP {error.code}"
        else:
            reason = error.__class__.__name__
        print(
            f"GitHub public API unavailable ({reason}); using the verified local snapshot.",
            file=sys.stderr,
        )
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
        '    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }\n'
        '  </style>\n'
    )


def text(x: int, y: int, value: str, size: int, color: str, *, weight: int = 400,
         tracking: float = 0, anchor: str = 'start', mono: bool = False) -> str:
    css = ' class="mono"' if mono else ''
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" letter-spacing="{tracking}" text-anchor="{anchor}"{css}>'
            f'{escape(value)}</text>')


def hero_svg(config: dict, theme: str, *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    identity = config['identity']
    width, height = (640, 420) if mobile else (1200, 320)
    parts = [svg_start(width, height, '130U — Mathematical finance and intelligent systems',
                       'Research in certified option valuation and engineering for agent evaluation and research workflows.'),
             f'<rect width="{width}" height="{height}" rx="20" fill="{p["bg_a"]}"/>']
    if mobile:
        parts.extend([
            text(40, 58, identity['eyebrow'], 22, p['muted'], weight=600, tracking=1),
            text(38, 143, identity['headline'], 51, p['ink'], weight=650, tracking=-1.7),
            text(38, 207, identity['subheadline'], 51, p['ink'], weight=650, tracking=-1.7),
            f'<path d="M40 248 H600" stroke="{p["line"]}"/>',
            text(40, 299, 'Certified valuation. Agent evaluation.', 26, p['muted']),
            text(40, 339, 'Research tools and applied AI.', 26, p['muted']),
            text(40, 389, 'MATHEMATICS / COMPUTATION / ENGINEERING', 18, p['faint'], tracking=.6),
        ])
    else:
        parts.extend([
            text(56, 57, identity['eyebrow'], 19, p['muted'], weight=600, tracking=1.3),
            text(53, 139, identity['headline'], 65, p['ink'], weight=650, tracking=-2.2),
            text(53, 215, identity['subheadline'], 65, p['ink'], weight=650, tracking=-2.2),
            text(56, 274, identity['descriptor'], 22, p['muted']),
            f'<path d="M810 74 V248" stroke="{p["line"]}"/>',
            text(850, 104, 'MATHEMATICAL FINANCE', 18, p['blue'], weight=600, tracking=.8),
            text(850, 141, 'Asian options', 25, p['ink'], weight=500),
            text(850, 175, 'Rough Heston', 25, p['ink'], weight=500),
            text(850, 230, 'ENGINEERING & APPLIED AI', 18, p['muted'], weight=600, tracking=.5),
            text(850, 263, 'Evaluation & research tools', 23, p['ink']),
        ])
    parts.append('</svg>\n')
    return '\n'.join(parts)


def telemetry_svg(config: dict, data: dict, theme: str, generated_at: datetime,
                  *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    width, height = (640, 382) if mobile else (1200, 174)
    scope = len(config['language_source_repositories'])
    saved = data['source'] != 'GitHub public API'
    timestamp = data.get('snapshot_at') if saved else generated_at.isoformat()
    timestamp_label = parse_utc(timestamp).strftime('%d %b %Y UTC') if timestamp else 'date unavailable'
    snapshot = ('Saved snapshot' if saved else 'Updated') + ' · ' + timestamp_label
    metrics = [
        (data['public_commits'], 'Engineering commits', f'{scope} engineering projects'),
        (data['pull_requests'], 'Pull requests', f'{scope} engineering projects'),
        (data['public_repositories'], 'Public repositories', 'Public GitHub account'),
    ]
    parts = [svg_start(width, height, '130U — GitHub activity',
                      f'{metrics[0][0]} author-attributed engineering commits and {metrics[1][0]} pull requests across {scope} engineering projects; {metrics[2][0]} public repositories. {snapshot}.'),
             f'<rect width="{width}" height="{height}" rx="16" fill="{p["bg_a"]}"/>']
    if mobile:
        for index, (value, label, detail) in enumerate(metrics):
            y = 74 + index * 95
            parts.extend([text(38, y + 17, f'{value:,}', 56, p['ink'], weight=650, tracking=-1.5),
                          text(172, y, label, 27, p['ink'], weight=500),
                          text(172, y + 34, detail, 22, p['muted'])])
            if index < 2:
                parts.append(f'<path d="M38 {y+49} H602" stroke="{p["line"]}"/>')
        parts.append(text(38, 354, snapshot, 20, p['faint']))
    else:
        for index, (value, label, detail) in enumerate(metrics):
            x = 48 + index * 398
            parts.extend([text(x, 65, f'{value:,}', 44, p['ink'], weight=650, tracking=-1.1),
                          text(x, 101, label, 22, p['ink'], weight=500),
                          text(x, 131, detail, 18, p['muted'])])
            if index < 2:
                parts.append(f'<path d="M{x+350} 35 V133" stroke="{p["line"]}"/>')
        parts.append(text(1152, 157, snapshot, 16, p['faint'], anchor='end'))
    parts.append('</svg>\n')
    return '\n'.join(parts)


def build_assets(config: dict, data: dict, generated_at: datetime) -> dict[str, str]:
    assets = {}
    for theme in ('light', 'dark'):
        for mobile in (False, True):
            variant = f'mobile-{theme}' if mobile else theme
            assets[f'hero-{variant}.svg'] = hero_svg(config, theme, mobile=mobile)
            assets[f'telemetry-{variant}.svg'] = telemetry_svg(config, data, theme, generated_at, mobile=mobile)
    return assets


def write_assets(config: dict, data: dict, generated_at: datetime | None = None) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in build_assets(config, data, generated_at).items():
        (OUTPUT_DIR / filename).write_text(content, encoding='utf-8', newline='\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help="Fetch current metrics from GitHub's public API")
    args = parser.parse_args()
    config = load_config()
    data = resolve_profile_data(config, args.live)
    write_assets(config, data)
    print(f"Generated eight static SVG assets from {data['source']}.")


if __name__ == '__main__':
    main()
