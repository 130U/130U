#!/usr/bin/env python3
"""Generate original, self-contained SVG assets for the 130U Profile README."""

from __future__ import annotations

import argparse
import json
import math
import random
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
        "bg_a": "#F9FAFC",
        "bg_b": "#EEF3FA",
        "surface": "#FFFFFF",
        "surface_2": "#F5F7FB",
        "ink": "#13213A",
        "muted": "#475569",
        "faint": "#5B6B82",
        "line": "#D7E0EC",
        "blue": "#2563EB",
        "cyan": "#0891B2",
        "violet": "#7C3AED",
        "amber": "#D97706",
        "green": "#0F8A65",
        "shadow": "#92A7C2",
    },
    "dark": {
        "bg_a": "#1A2437",
        "bg_b": "#24324A",
        "surface": "#202C42",
        "surface_2": "#26354F",
        "ink": "#F6F8FC",
        "muted": "#C7D2E3",
        "faint": "#AAB7CB",
        "line": "#3C4D68",
        "blue": "#72A2FF",
        "cyan": "#55C7D9",
        "violet": "#B59AF5",
        "amber": "#F0B55A",
        "green": "#61C7A5",
        "shadow": "#0C1320",
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
        f"  <title id=\"title\">{escape(title)}</title>\n"
        f"  <desc id=\"desc\">{escape(description)}</desc>\n"
        "  <!-- Generated by scripts/generate_profile.py; no external assets or scripts. -->\n"
    )


def svg_style(rules: str, reduced_motion_selectors: str, *, static_seconds: bool = False) -> str:
    rules = "\n".join(line.rstrip() for line in rules.strip().splitlines())
    seconds_fallback = (
        """
      .seconds-frame { opacity:0 !important; }
      .seconds-static { opacity:1 !important; }"""
        if static_seconds
        else ""
    )
    return f"""
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
{rules}
    @media (prefers-reduced-motion: reduce) {{
      {reduced_motion_selectors} {{ animation: none !important; }}{seconds_fallback}
    }}
  </style>
"""


def hero_style(*, mobile: bool) -> str:
    viewport = "mobile" if mobile else "desktop"
    orbit_rules = """
    .orbiter-mobile-a { animation: orbitMobileA 4.6s cubic-bezier(.2,.8,.2,1) 1 both; }
    .orbiter-mobile-b { animation: orbitMobileB 4.8s cubic-bezier(.2,.8,.2,1) 1 both; }
    @keyframes orbitMobileA {
      0%,100% { transform: translate(0,0); } 12.5% { transform: translate(-53.9px,49.5px); }
      25% { transform: translate(-184px,70px); } 37.5% { transform: translate(-314.1px,49.5px); }
      50% { transform: translate(-368px,0); } 62.5% { transform: translate(-314.1px,-49.5px); }
      75% { transform: translate(-184px,-70px); } 87.5% { transform: translate(-53.9px,-49.5px); }
    }
    @keyframes orbitMobileB {
      0%,100% { transform: translate(0,0); } 12.5% { transform: translate(73.2px,-77.8px); }
      25% { transform: translate(250px,-110px); } 37.5% { transform: translate(426.8px,-77.8px); }
      50% { transform: translate(500px,0); } 62.5% { transform: translate(426.8px,77.8px); }
      75% { transform: translate(250px,110px); } 87.5% { transform: translate(73.2px,77.8px); }
    }""" if mobile else """
    .orbit-track { animation: dashFlow 4.6s linear 1 both; }
    .orbiter-a { animation: orbitA 4.6s cubic-bezier(.2,.8,.2,1) 1 both; }
    .orbiter-b { animation: orbitB 4.7s cubic-bezier(.2,.8,.2,1) 1 both; }
    .orbiter-c { animation: orbitC 4.8s cubic-bezier(.2,.8,.2,1) 1 both; }
    @keyframes dashFlow { to { stroke-dashoffset: -44; } }
    @keyframes orbitA {
      0%,100% { transform: translate(0,0); } 12.5% { transform: translate(-40.4px,38.2px); }
      25% { transform: translate(-138px,54px); } 37.5% { transform: translate(-235.6px,38.2px); }
      50% { transform: translate(-276px,0); } 62.5% { transform: translate(-235.6px,-38.2px); }
      75% { transform: translate(-138px,-54px); } 87.5% { transform: translate(-40.4px,-38.2px); }
    }
    @keyframes orbitB {
      0%,100% { transform: translate(0,0); } 12.5% { transform: translate(58px,-58px); }
      25% { transform: translate(198px,-82px); } 37.5% { transform: translate(338px,-58px); }
      50% { transform: translate(396px,0); } 62.5% { transform: translate(338px,58px); }
      75% { transform: translate(198px,82px); } 87.5% { transform: translate(58px,58px); }
    }
    @keyframes orbitC {
      0%,100% { transform: translate(0,0); } 12.5% { transform: translate(-75.6px,79.2px); }
      25% { transform: translate(-258px,112px); } 37.5% { transform: translate(-440.4px,79.2px); }
      50% { transform: translate(-516px,0); } 62.5% { transform: translate(-440.4px,-79.2px); }
      75% { transform: translate(-258px,-112px); } 87.5% { transform: translate(-75.6px,-79.2px); }
    }"""
    core_class = f"core-{viewport}"
    core_origin = "360px 396px" if mobile else "870px 188px"
    rules = f"""
    .{core_class} {{ transform-box:view-box; transform-origin:{core_origin}; animation:coreBreathe 3.8s ease-out 1 both; }}
    .float-a {{ animation:floatY 4.2s ease-out 1 both; }}
    .float-b {{ animation:floatX 4.4s ease-out 1 both; }}
    {orbit_rules}
    @keyframes coreBreathe {{ 0%,100% {{ transform:scale(1); }} 50% {{ transform:scale(1.025); }} }}
    @keyframes floatY {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(3px); }} }}
    @keyframes floatX {{ 0%,100% {{ transform:translateX(0); }} 50% {{ transform:translateX(3px); }} }}"""
    selectors = [f".{core_class}", ".float-a", ".float-b"]
    if mobile:
        selectors.extend((".orbiter-mobile-a", ".orbiter-mobile-b"))
    else:
        rules += """
    .twinkle { transform-box:fill-box; transform-origin:center; animation:twinkle 3.2s ease-out 1 both; }
    .delay-1 { animation-delay:.12s; } .delay-2 { animation-delay:.24s; } .delay-3 { animation-delay:.36s; }
    @keyframes twinkle { 0%,100% { opacity:.42; transform:scale(1); } 50% { opacity:.78; transform:scale(1.18); } }"""
        selectors.extend((".orbit-track", ".orbiter-a", ".orbiter-b", ".orbiter-c", ".twinkle"))
    return svg_style(rules, ", ".join(selectors))


def telemetry_style(*, mobile: bool) -> str:
    runner_class = "metric-runner-mobile" if mobile else "metric-runner-desktop"
    hand_class = "seconds-hand-mobile" if mobile else "seconds-hand-desktop"
    runner_distance = 132 if mobile else 246
    hand_origin = "590px 223px" if mobile else "650px 210px"
    rules = f"""
    .metric-pulse {{ transform-box:fill-box; transform-origin:center; animation:signalPulse 2.8s ease-out 1 both; }}
    .seconds-frame {{ opacity:0; animation:secondFrame 60s steps(1,end) infinite; }}
    .seconds-static {{ opacity:0; }}
    .{hand_class} {{ transform-box:view-box; transform-origin:{hand_origin}; animation:secondsSweep 60s linear infinite; }}
    .{runner_class} {{ animation:metricRunner 4.2s ease-out 1 both; }}
    .delay-1 {{ animation-delay:.12s; }} .delay-2 {{ animation-delay:.24s; }} .delay-3 {{ animation-delay:.36s; }}
    @keyframes signalPulse {{ 0%,100% {{ opacity:.72; transform:scale(1); }} 50% {{ opacity:1; transform:scale(1.14); }} }}
    @keyframes secondFrame {{ 0%,1.64% {{ opacity:1; }} 1.67%,100% {{ opacity:0; }} }}
    @keyframes secondsSweep {{ to {{ transform:rotate(360deg); }} }}
    @keyframes metricRunner {{ 0%,100% {{ transform:translateX(0); }} 50% {{ transform:translateX({runner_distance}px); }} }}"""
    selectors = ", ".join((".metric-pulse", ".seconds-frame", f".{hand_class}", f".{runner_class}"))
    return svg_style(rules, selectors, static_seconds=True)


def signals_style(*, mobile: bool) -> str:
    sweep_class = "research-sweep-mobile" if mobile else "research-sweep-desktop"
    sweep_origin = "360px 720px" if mobile else "950px 280px"
    rules = f"""
    .bar-flow {{ animation:barGlow 3.6s ease-out 1 both; }}
    .bar-scan {{ animation:barScan 4.8s ease-out 1 both; }}
    .node-pulse {{ transform-box:fill-box; transform-origin:center; animation:nodePulse 3s ease-out 1 both; }}
    .{sweep_class} {{ transform-box:view-box; transform-origin:{sweep_origin}; animation:researchSweep 4.8s ease-out 1 both; }}
    .delay-1 {{ animation-delay:.12s; }} .delay-2 {{ animation-delay:.24s; }} .delay-3 {{ animation-delay:.36s; }}
    @keyframes barGlow {{ 0% {{ opacity:.72; }} 55%,100% {{ opacity:1; }} }}
    @keyframes barScan {{ 0% {{ opacity:0; transform:translateX(-92px); }} 12%,72% {{ opacity:.72; }} 100% {{ opacity:0; transform:translateX(430px); }} }}
    @keyframes nodePulse {{ 0%,100% {{ opacity:.72; transform:scale(1); }} 50% {{ opacity:1; transform:scale(1.16); }} }}
    @keyframes researchSweep {{ to {{ transform:rotate(360deg); }} }}"""
    selectors = ", ".join((".bar-flow", ".bar-scan", ".node-pulse", f".{sweep_class}"))
    return svg_style(rules, selectors)


def elapsed_parts(created: datetime, generated_at: datetime) -> tuple[int, int, int, int]:
    total_seconds = max(0, int((generated_at - created).total_seconds()))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, hours, minutes, seconds


def clock_ticks(cx: float, cy: float, inner: float, outer: float, color: str) -> list[str]:
    ticks = []
    for index in range(60):
        angle = math.radians(index * 6 - 90)
        tick_inner = inner - 5 if index % 5 == 0 else inner
        x1 = cx + tick_inner * math.cos(angle)
        y1 = cy + tick_inner * math.sin(angle)
        x2 = cx + outer * math.cos(angle)
        y2 = cy + outer * math.sin(angle)
        width = 2 if index % 5 == 0 else 1
        opacity = ".72" if index % 5 == 0 else ".28"
        ticks.append(
            f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" opacity="{opacity}"/>'
        )
    return ticks


def seconds_frames(start_second: int, x: float, y: float, color: str, font_size: int) -> list[str]:
    frames = [
        f'  <text class="seconds-static mono" x="{x}" y="{y}" text-anchor="middle" '
        f'fill="{color}" font-size="{font_size}" font-weight="760">{start_second:02d}</text>'
    ]
    for value in range(60):
        offset = (start_second - value) % 60
        frames.append(
            f'  <text class="seconds-frame mono" style="animation-delay:-{offset}s" x="{x}" y="{y}" '
            f'text-anchor="middle" fill="{color}" font-size="{font_size}" font-weight="760">{value:02d}</text>'
        )
    return frames


def hero_svg(config: dict, theme: str) -> str:
    p = PALETTES[theme]
    identity = config["identity"]
    signals = config["hero_signals"]
    rng = random.Random(130)
    stars = []
    for index in range(34):
        x = rng.randint(36, 1164)
        y = rng.randint(28, 332)
        radius = rng.choice((1, 1, 1.4, 1.8))
        opacity = rng.choice((0.22, 0.32, 0.45, 0.6))
        cls = f"twinkle delay-{index % 4}" if index % 3 == 0 else ""
        stars.append(
            f'  <circle class="{cls}" cx="{x}" cy="{y}" r="{radius}" fill="{p["faint"]}" opacity="{opacity}"/>'
        )

    labels = [
        (signals[0], 758, 72, p["blue"]),
        (signals[1], 1001, 95, p["violet"]),
        (signals[2], 1060, 204, p["cyan"]),
        (signals[3], 920, 310, p["amber"]),
        (signals[4], 712, 286, p["green"]),
        (signals[5], 710, 147, p["blue"]),
    ]

    parts = [
        svg_start(
            1200,
            360,
            "130U systems research signal map",
            "A light galaxy-inspired map connecting agentic AI, evaluation, research operations, embodied AI, product systems, and evidence design.",
        ),
        hero_style(mobile=False),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <radialGradient id="core"><stop stop-color="{p["surface"]}"/><stop offset=".55" stop-color="{p["surface_2"]}"/><stop offset="1" stop-color="{p["blue"]}" stop-opacity=".18"/></radialGradient>',
        f'    <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="{p["shadow"]}" flood-opacity=".18"/></filter>',
        "  </defs>",
        f'  <rect x="1" y="1" width="1198" height="358" rx="28" fill="url(#bg)" stroke="{p["line"]}"/>',
        f'  <circle cx="102" cy="44" r="150" fill="{p["cyan"]}" opacity=".035"/>',
        f'  <circle cx="1128" cy="326" r="190" fill="{p["violet"]}" opacity=".045"/>',
        *stars,
        f'  <text x="68" y="70" fill="{p["blue"]}" font-size="12" font-weight="700" letter-spacing="3.2">{escape(identity["eyebrow"])}</text>',
        f'  <text x="68" y="136" fill="{p["ink"]}" font-size="41" font-weight="760" letter-spacing="-1.4">{escape(identity["headline"])}</text>',
        f'  <text x="68" y="185" fill="{p["ink"]}" font-size="41" font-weight="360" letter-spacing="-1.2">{escape(identity["subheadline"])}</text>',
        f'  <line x1="68" y1="229" x2="388" y2="229" stroke="{p["line"]}"/>',
        f'  <text class="mono" x="68" y="260" fill="{p["muted"]}" font-size="12" letter-spacing="1.8">{escape(identity["descriptor"])}</text>',
        f'  <text x="68" y="316" fill="{p["faint"]}" font-size="13">A public field map of the questions I am pursuing now.</text>',
        f'  <g opacity=".65"><ellipse class="orbit-track" cx="870" cy="188" rx="258" ry="112" fill="none" stroke="{p["line"]}" stroke-width="1" stroke-dasharray="3 8"/><circle class="orbiter-c" cx="1128" cy="188" r="5" fill="{p["amber"]}"/></g>',
        f'  <g opacity=".8"><ellipse cx="870" cy="188" rx="198" ry="82" fill="none" stroke="{p["violet"]}" stroke-width="1.2" stroke-opacity=".55"/><circle class="orbiter-b" cx="672" cy="188" r="6" fill="{p["violet"]}"/></g>',
        f'  <g><ellipse cx="870" cy="188" rx="138" ry="54" fill="none" stroke="{p["cyan"]}" stroke-width="1.5" stroke-opacity=".7"/><circle class="orbiter-a" cx="1008" cy="188" r="6" fill="{p["cyan"]}"/></g>',
        f'  <g filter="url(#shadow)" class="core-desktop"><circle cx="870" cy="188" r="55" fill="url(#core)" stroke="{p["blue"]}" stroke-opacity=".34"/><circle cx="870" cy="188" r="42" fill="none" stroke="{p["blue"]}" stroke-opacity=".18"/><text x="870" y="197" text-anchor="middle" fill="{p["ink"]}" font-size="28" font-weight="760" letter-spacing="-1">130U</text></g>',
    ]
    for index, (label, x, y, color) in enumerate(labels):
        width = max(88, len(label) * 7.1 + 28)
        cls = "float-a" if index % 2 == 0 else "float-b"
        parts.extend(
            [
                f'  <g class="{cls}">',
                f'    <rect x="{x - width / 2:.1f}" y="{y - 18}" width="{width:.1f}" height="30" rx="15" fill="{p["surface"]}" fill-opacity=".82" stroke="{p["line"]}"/>',
                f'    <circle cx="{x - width / 2 + 14:.1f}" cy="{y - 3}" r="3.5" fill="{color}"/>',
                f'    <text x="{x - width / 2 + 24:.1f}" y="{y + 1}" fill="{p["muted"]}" font-size="11.5" font-weight="600">{escape(label)}</text>',
                "  </g>",
            ]
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def telemetry_chronograph_svg(config: dict, data: dict, theme: str, generated_at: datetime) -> str:
    p = PALETTES[theme]
    created = parse_utc(data["created_at"])
    days, hours, minutes, seconds = elapsed_parts(created, generated_at)
    metrics = [
        (f'{data["public_commits"]}', "PROJECT COMMITS", "AUTHOR SEARCH / 4 REPOS", p["cyan"]),
        (f'{data["pull_requests"]}', "PULL REQUESTS", "AUTHOR SEARCH / 4 REPOS", p["violet"]),
        (f'{data["public_repositories"]}', "PUBLIC REPOSITORIES", "GITHUB PUBLIC API", p["amber"]),
    ]
    parts = [
        svg_start(1200, 430, "130U live build log", "A daily-synced GitHub account-age snapshot with a live sixty-second visual pulse, plus author commits and pull requests across four selected project repositories and a public repository count."),
        telemetry_style(mobile=False),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <radialGradient id="clockGlow"><stop stop-color="{p["blue"]}" stop-opacity=".16"/><stop offset="1" stop-color="{p["blue"]}" stop-opacity="0"/></radialGradient>',
        f'    <filter id="softShadow" x="-20%" y="-30%" width="140%" height="160%"><feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="{p["shadow"]}" flood-opacity=".12"/></filter>',
        "  </defs>",
        f'  <rect x="1" y="1" width="1198" height="428" rx="28" fill="url(#bg)" stroke="{p["line"]}"/>',
        f'  <circle cx="76" cy="84" r="170" fill="{p["blue"]}" opacity=".025"/>',
        f'  <text x="54" y="48" fill="{p["blue"]}" font-size="11" font-weight="700" letter-spacing="3">BUILD LOG</text>',
        f'  <text x="1146" y="48" text-anchor="end" fill="{p["faint"]}" font-size="11">DAILY-SYNCED DATA / LIVE 60-SECOND PULSE</text>',
        f'  <rect x="54" y="76" width="720" height="310" rx="28" fill="{p["surface"]}" fill-opacity=".78" stroke="{p["blue"]}" stroke-opacity=".26" filter="url(#softShadow)"/>',
        f'  <text x="86" y="116" fill="{p["muted"]}" font-size="12" font-weight="700" letter-spacing="1.8">ACCOUNT AGE / LAST SYNC</text>',
        f'  <text x="742" y="116" text-anchor="end" fill="{p["faint"]}" font-size="10.5">{generated_at.strftime("%d %b %Y / %H:%M UTC").upper()}</text>',
        f'  <line x1="86" y1="136" x2="742" y2="136" stroke="{p["line"]}"/>',
        f'  <text class="mono" x="142" y="233" text-anchor="middle" fill="{p["ink"]}" font-size="82" font-weight="780" letter-spacing="-3">{days}</text>',
        f'  <text class="mono" x="318" y="227" text-anchor="middle" fill="{p["ink"]}" font-size="58" font-weight="760" letter-spacing="-2">{hours:02d}</text>',
        f'  <text class="mono" x="482" y="227" text-anchor="middle" fill="{p["ink"]}" font-size="58" font-weight="760" letter-spacing="-2">{minutes:02d}</text>',
        f'  <text x="230" y="219" text-anchor="middle" fill="{p["line"]}" font-size="34">:</text>',
        f'  <text x="400" y="219" text-anchor="middle" fill="{p["line"]}" font-size="34">:</text>',
        f'  <text x="566" y="219" text-anchor="middle" fill="{p["line"]}" font-size="34">:</text>',
        f'  <circle cx="650" cy="210" r="82" fill="url(#clockGlow)"/>',
        f'  <circle cx="650" cy="210" r="66" fill="none" stroke="{p["blue"]}" stroke-opacity=".20"/>',
        *clock_ticks(650, 210, 57, 63, p["blue"]),
        f'  <g transform="rotate({seconds * 6} 650 210)"><g class="seconds-hand-desktop"><line x1="650" y1="210" x2="650" y2="157" stroke="{p["blue"]}" stroke-width="3" stroke-linecap="round"/><circle cx="650" cy="157" r="4.5" fill="{p["blue"]}"/><circle cx="650" cy="210" r="5" fill="{p["surface"]}" stroke="{p["blue"]}" stroke-width="2"/></g></g>',
        *seconds_frames(seconds, 650, 221, p["ink"], 32),
        f'  <text class="mono" x="142" y="274" text-anchor="middle" fill="{p["muted"]}" font-size="10" letter-spacing="1.6">DAYS</text>',
        f'  <text class="mono" x="318" y="274" text-anchor="middle" fill="{p["muted"]}" font-size="10" letter-spacing="1.6">HOURS</text>',
        f'  <text class="mono" x="482" y="274" text-anchor="middle" fill="{p["muted"]}" font-size="10" letter-spacing="1.6">MINUTES</text>',
        f'  <text class="mono" x="650" y="296" text-anchor="middle" fill="{p["blue"]}" font-size="10" font-weight="700" letter-spacing="1.6">SECONDS</text>',
        f'  <rect x="86" y="316" width="656" height="42" rx="14" fill="{p["surface_2"]}" stroke="{p["line"]}"/>',
        f'  <circle class="metric-pulse" cx="107" cy="337" r="4" fill="{p["blue"]}"/>',
        f'  <text x="122" y="341" fill="{p["muted"]}" font-size="11">Age values refresh daily; the seconds readout and hand run live while this SVG is open.</text>',
    ]
    for index, (value, label, source, color) in enumerate(metrics):
        y = (76, 178, 280)[index]
        parts.extend(
            [
                f'  <rect x="800" y="{y}" width="346" height="90" rx="22" fill="{p["surface"]}" fill-opacity=".72" stroke="{p["line"]}"/>',
                f'  <line x1="828" y1="{y + 21}" x2="1098" y2="{y + 21}" stroke="{p["line"]}" stroke-linecap="round"/>',
                f'  <circle class="metric-runner-desktop delay-{index + 1}" cx="834" cy="{y + 21}" r="4" fill="{color}"/>',
                f'  <text class="mono" x="842" y="{y + 67}" fill="{p["ink"]}" font-size="34" font-weight="760" letter-spacing="-1">{escape(value)}</text>',
                f'  <text x="930" y="{y + 53}" fill="{p["ink"]}" font-size="12.5" font-weight="700">{label}</text>',
                f'  <text class="mono" x="930" y="{y + 72}" fill="{p["muted"]}" font-size="8.5" letter-spacing=".8">{source}</text>',
                f'  <circle class="metric-pulse delay-{index + 1}" cx="1116" cy="{y + 60}" r="6" fill="none" stroke="{color}" stroke-width="2"/>',
            ]
        )
    parts.extend(
        [
            f'  <text x="1146" y="414" text-anchor="end" fill="{p["faint"]}" font-size="9.5">CLICK THE PANEL FOR UPDATE HISTORY / USE THE LINKS BELOW FOR SOURCE VIEWS</text>',
            "</svg>\n",
        ]
    )
    return "\n".join(parts)


def normalized_languages(raw: dict, limit: int = 6) -> list[tuple[str, float]]:
    ranked = sorted(((str(name), float(value)) for name, value in raw.items() if float(value) > 0), key=lambda item: item[1], reverse=True)
    total = sum(value for _, value in ranked) or 1
    return [(name, value / total * 100) for name, value in ranked[:limit]]


def polar_point(cx: float, cy: float, radius: float, angle_degrees: float) -> tuple[float, float]:
    angle = math.radians(angle_degrees - 90)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def signals_grand_svg(config: dict, data: dict, theme: str) -> str:
    p = PALETTES[theme]
    languages = normalized_languages(data["languages"])
    sectors = config["focus_sectors"]
    accents = [p["blue"], p["cyan"], p["violet"], p["amber"], p["green"], p["faint"]]
    bar_x, bar_width, start_y = 205, 382, 120
    parts = [
        svg_start(1200, 520, "130U code signals and research orbit", "A large-format map of GitHub Linguist code proportions across four selected public repositories and evidence nodes for three current research sectors, with a finite evidence scan."),
        signals_style(mobile=False),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{p["surface"]}" stop-opacity="0"/><stop offset=".5" stop-color="{p["surface"]}" stop-opacity=".92"/><stop offset="1" stop-color="{p["surface"]}" stop-opacity="0"/></linearGradient>',
    ]
    for index, (_, percentage) in enumerate(languages):
        y = start_y + index * 54
        parts.append(f'    <clipPath id="barclip{index}"><rect x="{bar_x}" y="{y - 7}" width="{bar_width * percentage / 100:.1f}" height="18" rx="9"/></clipPath>')
    parts.extend(
        [
            "  </defs>",
            f'  <rect x="1" y="1" width="1198" height="518" rx="28" fill="url(#bg)" stroke="{p["line"]}"/>',
            f'  <circle cx="1138" cy="470" r="210" fill="{p["violet"]}" opacity=".025"/>',
            f'  <text x="54" y="50" fill="{p["blue"]}" font-size="11" font-weight="700" letter-spacing="3">CODE SIGNALS</text>',
            f'  <text x="704" y="50" fill="{p["violet"]}" font-size="11" font-weight="700" letter-spacing="3">RESEARCH ORBIT</text>',
            f'  <text x="54" y="76" fill="{p["faint"]}" font-size="11">GitHub Linguist bytes / four selected public code repositories</text>',
            f'  <text x="704" y="76" fill="{p["faint"]}" font-size="11">Evidence nodes map visible systems and studies / not proficiency</text>',
            f'  <line x1="646" y1="38" x2="646" y2="472" stroke="{p["line"]}"/>',
        ]
    )
    for index, (name, percentage) in enumerate(languages):
        y = start_y + index * 54
        color = accents[index % len(accents)]
        parts.extend(
            [
                f'  <text x="54" y="{y + 8}" fill="{p["ink"]}" font-size="15" font-weight="650">{escape(name)}</text>',
                f'  <rect x="{bar_x}" y="{y - 7}" width="{bar_width}" height="18" rx="9" fill="{p["line"]}" opacity=".55"/>',
                f'  <rect class="bar-flow delay-{index % 4}" x="{bar_x}" y="{y - 7}" width="{bar_width * percentage / 100:.1f}" height="18" rx="9" fill="{color}"/>',
                f'  <rect class="bar-scan delay-{index % 4}" x="{bar_x}" y="{y - 7}" width="76" height="18" fill="url(#scan)" clip-path="url(#barclip{index})"/>',
                f'  <text class="mono" x="610" y="{y + 8}" text-anchor="end" fill="{p["muted"]}" font-size="11.5">{percentage:.1f}%</text>',
            ]
        )

    cx, cy, radius = 950.0, 280.0, 150.0
    for ring in (50, 100, 150):
        parts.append(f'  <circle cx="{cx}" cy="{cy}" r="{ring}" fill="none" stroke="{p["line"]}" stroke-width="1"/>')
    centers = (0.0, 120.0, 240.0)
    label_positions = ((950, 108, "middle"), (1140, 458, "end"), (756, 458, "start"))
    for index, sector in enumerate(sectors):
        center_angle = centers[index]
        start = polar_point(cx, cy, radius, center_angle - 55)
        end = polar_point(cx, cy, radius, center_angle + 55)
        color = accents[index]
        parts.extend(
            [
                f'  <path d="M {cx:.1f} {cy:.1f} L {start[0]:.1f} {start[1]:.1f} A {radius:.1f} {radius:.1f} 0 0 1 {end[0]:.1f} {end[1]:.1f} Z" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-opacity=".55"/>',
                f'  <line x1="{cx}" y1="{cy}" x2="{polar_point(cx, cy, radius, center_angle)[0]:.1f}" y2="{polar_point(cx, cy, radius, center_angle)[1]:.1f}" stroke="{color}" stroke-opacity=".42"/>',
            ]
        )
        node_count = int(sector["nodes"])
        for node_index in range(node_count):
            node_radius = 66 + node_index * 29
            node_angle = center_angle + (node_index - (node_count - 1) / 2) * 14
            node = polar_point(cx, cy, node_radius, node_angle)
            parts.append(f'  <circle class="node-pulse delay-{(index + node_index) % 4}" cx="{node[0]:.1f}" cy="{node[1]:.1f}" r="7" fill="{color}" stroke="{p["surface"]}" stroke-width="2.5"/>')
        label_x, label_y, anchor = label_positions[index]
        parts.extend(
            [
                f'  <text x="{label_x}" y="{label_y}" text-anchor="{anchor}" fill="{p["ink"]}" font-size="12" font-weight="700">{escape(sector["label"])}</text>',
                f'  <text class="mono" x="{label_x}" y="{label_y + 20}" text-anchor="{anchor}" fill="{p["muted"]}" font-size="9.5">{escape(sector["evidence"]).upper()}</text>',
            ]
        )
    parts.extend(
        [
            f'  <g class="research-sweep-desktop"><line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - radius + 8}" stroke="{p["violet"]}" stroke-width="2" stroke-linecap="round" opacity=".72"/><circle cx="{cx}" cy="{cy - radius + 8}" r="5" fill="{p["violet"]}"/></g>',
            f'  <circle cx="{cx}" cy="{cy}" r="5" fill="{p["ink"]}"/>',
            f'  <text x="1146" y="498" text-anchor="end" fill="{p["faint"]}" font-size="9.5">BARS SHOW CODE PROPORTION / NODES SHOW PUBLIC EVIDENCE / CLICK TO EXPLORE</text>',
            "</svg>\n",
        ]
    )
    return "\n".join(parts)


def hero_mobile_svg(config: dict, theme: str) -> str:
    p = PALETTES[theme]
    identity = config["identity"]
    signals = config["hero_signals"]
    labels = [
        (signals[0], 88, 346, p["blue"]),
        (signals[1], 510, 346, p["violet"]),
        (signals[2], 530, 437, p["cyan"]),
        (signals[3], 419, 516, p["amber"]),
        (signals[4], 78, 437, p["green"]),
        (signals[5], 218, 516, p["blue"]),
    ]
    parts = [
        svg_start(720, 560, "130U mobile systems research atlas", "A mobile light-galaxy identity atlas for 130U systems research."),
        hero_style(mobile=True),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <radialGradient id="core"><stop stop-color="{p["surface"]}"/><stop offset="1" stop-color="{p["blue"]}" stop-opacity=".2"/></radialGradient>',
        "  </defs>",
        f'  <rect x="1" y="1" width="718" height="558" rx="26" fill="url(#bg)" stroke="{p["line"]}"/>',
        f'  <circle cx="54" cy="45" r="120" fill="{p["cyan"]}" opacity=".04"/>',
        f'  <circle cx="676" cy="530" r="150" fill="{p["violet"]}" opacity=".05"/>',
        f'  <text x="44" y="58" fill="{p["blue"]}" font-size="14" font-weight="700" letter-spacing="3">{escape(identity["eyebrow"])}</text>',
        f'  <text x="44" y="119" fill="{p["ink"]}" font-size="36" font-weight="760" letter-spacing="-1.1">{escape(identity["headline"])}</text>',
        f'  <text x="44" y="163" fill="{p["ink"]}" font-size="36" font-weight="360" letter-spacing="-1">{escape(identity["subheadline"])}</text>',
        f'  <text class="mono" x="44" y="204" fill="{p["muted"]}" font-size="13" letter-spacing="1.2">{escape(identity["descriptor"])}</text>',
        f'  <line x1="44" y1="229" x2="676" y2="229" stroke="{p["line"]}"/>',
        f'  <text x="44" y="258" fill="{p["faint"]}" font-size="15">A public field map of the questions I am pursuing now.</text>',
        f'  <g><ellipse cx="360" cy="396" rx="250" ry="110" fill="none" stroke="{p["violet"]}" stroke-opacity=".55"/><circle class="orbiter-mobile-b" cx="110" cy="396" r="6" fill="{p["violet"]}"/></g>',
        f'  <g><ellipse cx="360" cy="396" rx="184" ry="70" fill="none" stroke="{p["cyan"]}" stroke-opacity=".7" stroke-width="1.5"/><circle class="orbiter-mobile-a" cx="544" cy="396" r="6" fill="{p["cyan"]}"/></g>',
        f'  <g class="core-mobile"><circle cx="360" cy="396" r="54" fill="url(#core)" stroke="{p["blue"]}" stroke-opacity=".35"/><text x="360" y="406" text-anchor="middle" fill="{p["ink"]}" font-size="28" font-weight="760">130U</text></g>',
    ]
    for index, (label, x, y, color) in enumerate(labels):
        cls = "float-a" if index % 2 == 0 else "float-b"
        parts.extend(
            [
                f'  <g class="{cls}">',
                f'    <circle cx="{x}" cy="{y - 4}" r="4" fill="{color}"/>',
                f'    <text x="{x + 11}" y="{y}" fill="{p["muted"]}" font-size="16" font-weight="600">{escape(label)}</text>',
                "  </g>",
            ]
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def telemetry_chronograph_mobile_svg(config: dict, data: dict, theme: str, generated_at: datetime) -> str:
    p = PALETTES[theme]
    created = parse_utc(data["created_at"])
    days, hours, minutes, seconds = elapsed_parts(created, generated_at)
    metrics = [
        (str(data["public_commits"]), "PROJECT COMMITS", p["cyan"]),
        (str(data["pull_requests"]), "PULL REQUESTS", p["violet"]),
        (str(data["public_repositories"]), "PUBLIC REPOS", p["amber"]),
    ]
    parts = [
        svg_start(720, 760, "130U mobile live build log", "A large mobile GitHub account-age snapshot with a live sixty-second visual pulse, plus public project telemetry."),
        telemetry_style(mobile=True),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <radialGradient id="clockGlow"><stop stop-color="{p["blue"]}" stop-opacity=".16"/><stop offset="1" stop-color="{p["blue"]}" stop-opacity="0"/></radialGradient>',
        "  </defs>",
        f'  <rect x="1" y="1" width="718" height="758" rx="28" fill="url(#bg)" stroke="{p["line"]}"/>',
        f'  <text x="40" y="46" fill="{p["blue"]}" font-size="14" font-weight="700" letter-spacing="3">BUILD LOG</text>',
        f'  <text x="680" y="46" text-anchor="end" fill="{p["faint"]}" font-size="12">DAILY DATA / LIVE SECONDS</text>',
        f'  <rect x="40" y="70" width="640" height="340" rx="26" fill="{p["surface"]}" fill-opacity=".76" stroke="{p["blue"]}" stroke-opacity=".26"/>',
        f'  <text x="72" y="110" fill="{p["muted"]}" font-size="14" font-weight="700" letter-spacing="1.4">ACCOUNT AGE / LAST SYNC</text>',
        f'  <text x="648" y="110" text-anchor="end" fill="{p["faint"]}" font-size="12">{generated_at.strftime("%d %b / %H:%M UTC").upper()}</text>',
        f'  <line x1="72" y1="130" x2="648" y2="130" stroke="{p["line"]}"/>',
        f'  <text class="mono" x="110" y="245" text-anchor="middle" fill="{p["ink"]}" font-size="68" font-weight="780" letter-spacing="-3">{days}</text>',
        f'  <text class="mono" x="275" y="240" text-anchor="middle" fill="{p["ink"]}" font-size="50" font-weight="760" letter-spacing="-2">{hours:02d}</text>',
        f'  <text class="mono" x="425" y="240" text-anchor="middle" fill="{p["ink"]}" font-size="50" font-weight="760" letter-spacing="-2">{minutes:02d}</text>',
        f'  <text x="193" y="232" text-anchor="middle" fill="{p["line"]}" font-size="30">:</text>',
        f'  <text x="350" y="232" text-anchor="middle" fill="{p["line"]}" font-size="30">:</text>',
        f'  <text x="506" y="232" text-anchor="middle" fill="{p["line"]}" font-size="30">:</text>',
        f'  <circle cx="590" cy="223" r="72" fill="url(#clockGlow)"/>',
        f'  <circle cx="590" cy="223" r="59" fill="none" stroke="{p["blue"]}" stroke-opacity=".20"/>',
        *clock_ticks(590, 223, 50, 56, p["blue"]),
        f'  <g transform="rotate({seconds * 6} 590 223)"><g class="seconds-hand-mobile"><line x1="590" y1="223" x2="590" y2="177" stroke="{p["blue"]}" stroke-width="3" stroke-linecap="round"/><circle cx="590" cy="177" r="4" fill="{p["blue"]}"/><circle cx="590" cy="223" r="5" fill="{p["surface"]}" stroke="{p["blue"]}" stroke-width="2"/></g></g>',
        *seconds_frames(seconds, 590, 233, p["ink"], 28),
        f'  <text class="mono" x="110" y="286" text-anchor="middle" fill="{p["muted"]}" font-size="13" letter-spacing="1.2">DAYS</text>',
        f'  <text class="mono" x="275" y="286" text-anchor="middle" fill="{p["muted"]}" font-size="13" letter-spacing="1.2">HOURS</text>',
        f'  <text class="mono" x="425" y="286" text-anchor="middle" fill="{p["muted"]}" font-size="13" letter-spacing="1.2">MINUTES</text>',
        f'  <text class="mono" x="590" y="311" text-anchor="middle" fill="{p["blue"]}" font-size="13" font-weight="700" letter-spacing="1.2">SECONDS</text>',
        f'  <rect x="72" y="335" width="576" height="48" rx="15" fill="{p["surface_2"]}" stroke="{p["line"]}"/>',
        f'  <circle class="metric-pulse" cx="94" cy="359" r="4" fill="{p["blue"]}"/>',
        f'  <text x="111" y="363" fill="{p["muted"]}" font-size="13">Daily age snapshot; live seconds run while this SVG is open.</text>',
    ]
    for index, (value, label, color) in enumerate(metrics):
        x = 40 + index * 218
        center = x + 102
        parts.extend(
            [
                f'  <rect x="{x}" y="445" width="204" height="210" rx="22" fill="{p["surface"]}" fill-opacity=".70" stroke="{p["line"]}"/>',
                f'  <line x1="{x + 28}" y1="478" x2="{x + 176}" y2="478" stroke="{p["line"]}" stroke-linecap="round"/>',
                f'  <circle class="metric-runner-mobile delay-{index + 1}" cx="{x + 30}" cy="478" r="4" fill="{color}"/>',
                f'  <text class="mono" x="{center}" y="558" text-anchor="middle" fill="{p["ink"]}" font-size="46" font-weight="760">{escape(value)}</text>',
                f'  <text class="mono" x="{center}" y="596" text-anchor="middle" fill="{p["muted"]}" font-size="13" letter-spacing=".8">{label}</text>',
                f'  <circle class="metric-pulse delay-{index + 1}" cx="{center}" cy="625" r="6" fill="none" stroke="{color}" stroke-width="2"/>',
            ]
        )
    parts.extend(
        [
            f'  <text x="680" y="730" text-anchor="end" fill="{p["faint"]}" font-size="11.5">CLICK FOR UPDATE HISTORY / SOURCE LINKS BELOW</text>',
            "</svg>\n",
        ]
    )
    return "\n".join(parts)


def signals_grand_mobile_svg(config: dict, data: dict, theme: str) -> str:
    p = PALETTES[theme]
    languages = normalized_languages(data["languages"])
    sectors = config["focus_sectors"]
    accents = [p["blue"], p["cyan"], p["violet"], p["amber"], p["green"], p["faint"]]
    bar_x, bar_width, start_y = 174, 418, 114
    parts = [
        svg_start(720, 1020, "130U mobile code signals and research orbit", "A large mobile map of GitHub Linguist code proportions and visible research evidence, with a finite evidence scan."),
        signals_style(mobile=True),
        "  <defs>",
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["bg_a"]}"/><stop offset="1" stop-color="{p["bg_b"]}"/></linearGradient>',
        f'    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{p["surface"]}" stop-opacity="0"/><stop offset=".5" stop-color="{p["surface"]}" stop-opacity=".92"/><stop offset="1" stop-color="{p["surface"]}" stop-opacity="0"/></linearGradient>',
    ]
    for index, (_, percentage) in enumerate(languages):
        y = start_y + index * 50
        parts.append(f'    <clipPath id="mobileBar{index}"><rect x="{bar_x}" y="{y - 6}" width="{bar_width * percentage / 100:.1f}" height="18" rx="9"/></clipPath>')
    parts.extend(
        [
            "  </defs>",
            f'  <rect x="1" y="1" width="718" height="1018" rx="28" fill="url(#bg)" stroke="{p["line"]}"/>',
            f'  <text x="40" y="48" fill="{p["blue"]}" font-size="14" font-weight="700" letter-spacing="3">CODE SIGNALS</text>',
            f'  <text x="40" y="74" fill="{p["faint"]}" font-size="14">GitHub Linguist bytes / four selected public code repositories</text>',
        ]
    )
    for index, (name, percentage) in enumerate(languages):
        y = start_y + index * 50
        color = accents[index]
        parts.extend(
            [
                f'  <text x="40" y="{y + 9}" fill="{p["ink"]}" font-size="16" font-weight="650">{escape(name)}</text>',
                f'  <rect x="{bar_x}" y="{y - 6}" width="{bar_width}" height="18" rx="9" fill="{p["line"]}" opacity=".55"/>',
                f'  <rect class="bar-flow delay-{index % 4}" x="{bar_x}" y="{y - 6}" width="{bar_width * percentage / 100:.1f}" height="18" rx="9" fill="{color}"/>',
                f'  <rect class="bar-scan delay-{index % 4}" x="{bar_x}" y="{y - 6}" width="76" height="18" fill="url(#scan)" clip-path="url(#mobileBar{index})"/>',
                f'  <text class="mono" x="674" y="{y + 9}" text-anchor="end" fill="{p["muted"]}" font-size="14">{percentage:.1f}%</text>',
            ]
        )
    parts.extend(
        [
            f'  <line x1="40" y1="421" x2="680" y2="421" stroke="{p["line"]}"/>',
            f'  <text x="40" y="466" fill="{p["violet"]}" font-size="14" font-weight="700" letter-spacing="3">RESEARCH ORBIT</text>',
            f'  <text x="40" y="492" fill="{p["faint"]}" font-size="14">Evidence nodes map visible systems and studies / not proficiency</text>',
        ]
    )
    cx, cy, radius = 360.0, 720.0, 185.0
    for ring in (62, 123, 185):
        parts.append(f'  <circle cx="{cx}" cy="{cy}" r="{ring}" fill="none" stroke="{p["line"]}"/>')
    centers = (0.0, 120.0, 240.0)
    label_positions = ((360, 515, "middle"), (662, 950, "end"), (58, 950, "start"))
    for index, sector in enumerate(sectors):
        angle = centers[index]
        start = polar_point(cx, cy, radius, angle - 55)
        end = polar_point(cx, cy, radius, angle + 55)
        color = accents[index]
        parts.append(f'  <path d="M {cx} {cy} L {start[0]:.1f} {start[1]:.1f} A {radius} {radius} 0 0 1 {end[0]:.1f} {end[1]:.1f} Z" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-opacity=".55"/>')
        node_count = int(sector["nodes"])
        for node_index in range(node_count):
            node = polar_point(cx, cy, 84 + node_index * 36, angle + (node_index - (node_count - 1) / 2) * 14)
            parts.append(f'  <circle class="node-pulse delay-{(index + node_index) % 4}" cx="{node[0]:.1f}" cy="{node[1]:.1f}" r="8" fill="{color}" stroke="{p["surface"]}" stroke-width="2.5"/>')
        lx, ly, anchor = label_positions[index]
        parts.extend(
            [
                f'  <text x="{lx}" y="{ly}" text-anchor="{anchor}" fill="{p["ink"]}" font-size="15" font-weight="700">{escape(sector["label"])}</text>',
                f'  <text class="mono" x="{lx}" y="{ly + 21}" text-anchor="{anchor}" fill="{p["muted"]}" font-size="12">{escape(sector["evidence"]).upper()}</text>',
            ]
        )
    parts.extend(
        [
            f'  <g class="research-sweep-mobile"><line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - radius + 10}" stroke="{p["violet"]}" stroke-width="2.5" stroke-linecap="round" opacity=".72"/><circle cx="{cx}" cy="{cy - radius + 10}" r="5" fill="{p["violet"]}"/></g>',
            f'  <circle cx="{cx}" cy="{cy}" r="5" fill="{p["ink"]}"/>',
            f'  <text x="680" y="994" text-anchor="end" fill="{p["faint"]}" font-size="11.5">CODE PROPORTION / PUBLIC EVIDENCE / CLICK TO EXPLORE</text>',
            "</svg>\n",
        ]
    )
    return "\n".join(parts)


def build_assets(config: dict, data: dict, generated_at: datetime) -> dict[str, str]:
    assets: dict[str, str] = {}
    for theme in ("light", "dark"):
        assets.update(
            {
                f"hero-{theme}.svg": hero_svg(config, theme),
                f"hero-mobile-{theme}.svg": hero_mobile_svg(config, theme),
                f"telemetry-{theme}.svg": telemetry_chronograph_svg(config, data, theme, generated_at),
                f"telemetry-mobile-{theme}.svg": telemetry_chronograph_mobile_svg(config, data, theme, generated_at),
                f"signals-{theme}.svg": signals_grand_svg(config, data, theme),
                f"signals-mobile-{theme}.svg": signals_grand_mobile_svg(config, data, theme),
            }
        )
    return assets


def write_assets(config: dict, data: dict, generated_at: datetime | None = None) -> None:
    generated_at = generated_at or datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in build_assets(config, data, generated_at).items():
        (OUTPUT_DIR / filename).write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch current metrics from GitHub's public API")
    args = parser.parse_args()
    config = load_config()
    data = resolve_profile_data(config, args.live)
    write_assets(config, data)
    print(f"Generated twelve SVG assets from {data['source']}.")


if __name__ == "__main__":
    main()
