#!/usr/bin/env python3
"""Build the static editorial headers and navigation controls for the profile."""

from pathlib import Path

from generate_profile import PALETTES, svg_start, text

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "layout"


def sheet_header(kind: str, theme: str, mobile: bool) -> str:
    p = PALETTES[theme]
    number, title, subtitle, count = (
        ("01", "AI Engineering", "Models, agents, and research tools.", "05 PROJECTS")
        if kind == "ai" else
        ("02", "Finance", "Mathematical research in valuation and risk.", "03 PAPERS")
    )
    width, height = (640, 256) if mobile else (1200, 188)
    left = 32 if mobile else 48
    parts = [svg_start(width, height, title, f"Portfolio sheet {number}. {subtitle}"),
             f'<rect width="{width}" height="{height}" fill="{p["bg_a"]}"/>',
             f'<path d="M{left} 30 H{left + 28}" stroke="{p["blue"]}" stroke-width="3"/>',
             text(left + 42, 35, f"{number} / SELECTED WORK", 22 if mobile else 14,
                  p["muted"], family="mono", tracking=1),
             text(left, 102 if mobile else 106, title, 60 if mobile else 58,
                  p["ink"], tracking=-1.7),
             text(left, 150 if mobile else 147, "Mathematical research" if mobile and kind == "finance" else subtitle, 28 if mobile else 25,
                  p["muted"], family="serif")]
    if mobile and kind == "finance":
        parts.append(text(left, 183, "in valuation and risk.", 28, p["muted"], family="serif"))
    if mobile:
        parts.append(text(left, 228, count, 24, p["muted"], family="mono", tracking=1))
    else:
        parts.extend([
            f'<path d="M1020 42 V148" stroke="{p["line"]}"/>',
            text(1060, 83, number, 43, p["ink"], family="serif"),
            text(1060, 125, count, 13, p["muted"], family="mono"),
        ])
    parts.append("</svg>\n")
    return "\n".join(parts)


BUTTONS = {
    "button-paper": ("Paper", 72, True),
    "button-repository": ("Repository", 100, False),
    "button-results": ("Results", 80, False),
    "button-model": ("Model", 76, False),
    "button-training": ("Training", 80, False),
    "button-analysis": ("Analysis", 96, False),
    "nav-ai": ("01 / AI Engineering", 168, True),
    "nav-finance": ("02 / Finance", 120, False),
}


def button(label: str, width: int, primary: bool) -> str:
    height = 38 if label.startswith(("01", "02")) else 32
    bg, ink = ("#191919", "#F7F6F5") if primary else ("#F7F6F5", "#191919")
    baseline = 24 if height == 38 else 21
    return "\n".join([
        svg_start(width, height, label, f"Open {label.lower()}"),
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" fill="{bg}" stroke="#8B8883"/>',
        text(12, baseline, label, 12, ink),
        f'<path d="M{width - 21} {height / 2 + 3} l6 -6 m-5 0 h5 v5" fill="none" stroke="{ink}" stroke-width="1.2"/>',
        "</svg>\n",
    ])


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for kind in ("ai", "finance"):
        for theme in ("light", "dark"):
            for mobile in (False, True):
                variant = f"mobile-{theme}" if mobile else theme
                (OUTPUT / f"sheet-{kind}-{variant}-v2.svg").write_text(
                    sheet_header(kind, theme, mobile), encoding="utf-8", newline="\n")
    for name, (label, width, primary) in BUTTONS.items():
        (OUTPUT / f"{name}-v2.svg").write_text(button(label, width, primary), encoding="utf-8", newline="\n")
    print("Generated 2 responsive sheet headers and 8 navigation controls.")


if __name__ == "__main__":
    main()
