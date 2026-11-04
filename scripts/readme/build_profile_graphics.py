#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools==4.67.0", "brotli==1.2.0", "uharfbuzz==0.56.3"]
# ///
"""Build the Netspeedy organization profile graphics in profile/assets/.

    netspeedy-banner.svg        name, role and focus, with a terminal taking a change from push to
                                applied, above the dotted Earth with London lit
    netspeedy-highlights.svg    four headline figures under the badge row
    netspeedy-signals.svg       three CV figures drawn to scale, the public tools, and the six
                                engineering focus areas
    netspeedy-how-we-work.svg   the six working principles as stages on one pipeline
    project-<name>.svg          a card per public project, from projects.json
    site-kubertech-*.svg        the two KuberTech sites
    link-*.svg                  the maintainer's CV and GitHub
    social-preview.svg/.png     the repository's 1280x640 social preview, from the banner

It also rewrites the Selected Public Work grid in profile/README.md, between the projects:start
and projects:end markers, from projects.json. Adding a public repository is an entry there and a
rebuild: its card, its place in the grid, its Homebrew tap badge, its tile in the signals graphic
and the tool counts all follow. AGENTS.md has the full steps.

This is a copy of soakes/soakes scripts/readme/build_profile_graphics.py, which builds Simon Oakes'
profile the same way, with the Netspeedy content and the netspeedy colours the org's own project
heroes use. Fixes to the shared parts (fonts, text measuring, the Earth, the terminal, the cards)
belong in both copies.

land.ts beside this script is a verbatim copy of soakes/cv src/lib/site/land.ts, the land bitmap
oakes.me.uk draws its globe from. icons.json holds the simple-icons paths for the card logos
(CC0-1.0, version recorded in the file); a project whose language logo isn't there stops the
build until it's added.

Inter and JetBrains Mono (SIL Open Font License 1.1) are the Google Fonts builds kept on
assets.netspeedy.io and pinned by checksum in FAMILIES, subset here to the characters each SVG
renders. Text is shaped with HarfBuzz, so it wraps where a browser would and anything that won't
fit stops the build. fontTools is pinned too, so a rebuild with the same content gives the same
bytes. Run it with `make readme-graphics` (uv installs the pinned tools); the first run needs
network access for the fonts, and the social preview PNG needs Chrome or Chromium (set CHROME
if it isn't found). `make check` reports whether anything is out of date without writing.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "profile" / "assets"
README = ROOT / "profile" / "README.md"
LAND = HERE / "land.ts"
ICONS = HERE / "icons.json"
PROJECTS_FILE = HERE / "projects.json"
WIDTH = 1200
# assets.netspeedy.io's Cloudflare zone turns away urllib's default user agent.
USER_AGENT = "netspeedy-readme-hero"
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
)

# The netspeedy project heroes' inks, cyan, blue and amber (s3ctl, joflux).
BG = "#060B13"
INK = "#F1F5FA"
INK_2 = "#B5C0CD"
INK_3 = "#808D9E"
CYAN = "#4BD8FF"
CYAN_2 = "#A8ECFF"
CYAN_3 = "#18A8FF"
AMBER = "#F5B841"
AMBER_2 = "#FDE1A7"
GREEN = "#3CD788"
# Terminal surfaces. The body is a flat colour because typing works by stepping a cover of the
# same colour off each command.
TERM_BODY = "#0A1019"
TERM_BAR = "#0F1622"
TERM_EDGE = "#223047"

# Fonts: css class -> (source font, its sha256, weight range, embedded family name). The
# sources are the Google Fonts builds of Inter 4.001 and JetBrains Mono 2.211, kept on
# assets.netspeedy.io and cached after the first download. A new version goes up there
# under a new filename, so these files never change.
FONT_HOST = "https://assets.netspeedy.io/versioned/fonts"
FONT_CACHE = Path.home() / ".cache" / "netspeedy-fonts"
FAMILIES = {
    "sans": (
        "inter-opsz-wght.4.001.ttf",
        "29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031",
        "400 800",
        "Profile Sans",
    ),
    "mono": (
        "jetbrains-mono-wght.2.211.ttf",
        "48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda",
        "400 700",
        "Profile Mono",
    ),
}
FONT_CSS = (
    ".sans{font-family:'Profile Sans',-apple-system,'Segoe UI','Helvetica Neue',Arial,"
    "sans-serif;font-optical-sizing:auto;}"
    ".mono{font-family:'Profile Mono','SF Mono',Menlo,Consolas,monospace;}"
)
TWINKLE_CSS = (
    ".tw{animation:tw 5.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
    ".tw1{animation-duration:6.4s}.tw2{animation-duration:4.6s}.tw3{animation-duration:7.3s}"
    "@keyframes tw{0%,100%{opacity:.85}50%{opacity:.15}}"
)

COPY_X = 64.0
COPY_RIGHT = 660.0  # nothing in a copy column may run past this

# Starfield: seeded, so rebuilding gives the same sky. No star sits behind copy or a scene.
STAR_SEED = 5
STARS = 120
TWINKLING = 18

# The Earth, from the soakes/cv README hero: an orthographic view of the land lattice, centred
# on the cv hero's (9, 27). The banner sizes it and says where London lands.
LONDON = (51.507, -0.128)
STEP = 0.66  # land lattice spacing in degrees
CV_VIEW = (9.0, 27.0)


# Fonts


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def font_source(name: str, sha256: str) -> bytes:
    """A pinned source font from FONT_HOST, checked against its sha256 and cached."""
    cached = FONT_CACHE / name
    if cached.exists():
        data = cached.read_bytes()
        if hashlib.sha256(data).hexdigest() == sha256:
            return data
    data = fetch(f"{FONT_HOST}/{name}")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"{FONT_HOST}/{name} doesn't match its pinned sha256")
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return data


def subset_font(source: bytes, text: str) -> bytes:
    """The variable font cut down to the given characters, as woff2.

    Every axis is kept: trimming them with fontTools' instancer moved the headline's
    pixels. The source's head timestamp is kept too, so the same text always gives the
    same bytes.
    """
    font = TTFont(io.BytesIO(source), recalcTimestamp=False)
    options = subset.Options()
    options.hinting = False
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def collect_chars(svg: str) -> dict[str, set[str]]:
    """Characters rendered by each font class, inherited through groups."""
    chars: dict[str, set[str]] = {name: set() for name in FAMILIES}

    def family_of(element: ET.Element, inherited: str | None) -> str | None:
        for cls in (element.get("class") or "").split():
            if cls in FAMILIES:
                return cls
        return inherited

    def walk(element: ET.Element, inherited: str | None, in_text: bool) -> None:
        tag = element.tag.split("}")[-1]
        family = family_of(element, inherited)
        if tag in ("style", "title", "desc", "script"):
            return
        is_text = in_text or tag in ("text", "tspan", "textPath")
        if is_text and tag in ("text", "tspan", "textPath") and element.text:
            if family is None:
                raise SystemExit(f"text without a font class: {element.text!r}")
            chars[family].update(element.text)
        for child in element:
            walk(child, family, is_text)
            if is_text and child.tail and child.tail.strip():
                chars[family or "sans"].update(child.tail)

    walk(ET.fromstring(svg), None, False)
    return chars


def font_faces(svg: str) -> str:
    """One @font-face per family, subset to exactly the characters the SVG renders."""
    chars = collect_chars(svg)
    faces = []
    for cls, (name, sha256, weights, local) in FAMILIES.items():
        used = chars[cls]
        if not used:
            continue
        text = "".join(sorted((used - set("\n\t\r")) | {" "}))
        data = base64.b64encode(subset_font(font_source(name, sha256), text)).decode()
        faces.append(
            f"@font-face{{font-family:'{local}';font-weight:{weights};"
            f"font-style:normal;src:url(data:font/woff2;base64,{data}) "
            "format('woff2');}"
        )
    return "".join(faces)


@cache
def shaper(weight: float, size: float) -> tuple[hb.Font, int]:
    name, sha256, _, _ = FAMILIES["sans"]
    face = hb.Face(font_source(name, sha256))
    font = hb.Font(face)
    # font-optical-sizing:auto follows the px size, within Inter's 14..32 range.
    font.set_variations({"wght": weight, "opsz": min(max(size, 14), 32)})
    return font, face.upem


def text_width(text: str, size: float, weight: float = 400, spacing: float = 0.0) -> float:
    """The advance of Inter text as a browser lays it out: shaped with kerning, plus CSS
    letter-spacing after every character."""
    if not text:
        return 0.0
    font, upem = shaper(weight, size)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True, "calt": True})
    return sum(pos.x_advance for pos in buf.glyph_positions) * size / upem + spacing * len(text)


def wrap(text: str, size: float, width: float, weight: float = 400) -> list[str]:
    """Inter text broken into lines no wider than `width`, a word at a time."""
    lines = [""]
    for word in text.split():
        trial = f"{lines[-1]} {word}".strip()
        if lines[-1] and text_width(trial, size, weight) > width:
            lines.append(word)
        else:
            lines[-1] = trial
    if any(text_width(line, size, weight) > width for line in lines):
        raise SystemExit(f"a word in {text!r} is wider than {width:.0f}px")
    return lines


# Small helpers


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def num(value: float) -> str:
    """One decimal place, without a trailing .0."""
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def mono_width(chars: int, size: float, spacing: float = 0.0) -> float:
    """JetBrains Mono advances exactly 0.6 em; letter-spacing applies per glyph."""
    return chars * (size * 0.6 + spacing)


def gradient(kind: str, attrs: str, stops: list[tuple[str, str, str]]) -> list[str]:
    lines = [f"    <{kind} {attrs}>"]
    for offset, colour, opacity in stops:
        alpha = f' stop-opacity="{opacity}"' if opacity else ""
        lines.append(f'      <stop offset="{offset}" stop-color="{colour}"{alpha} />')
    return [*lines, f"    </{kind}>"]


def pct(seconds: float, loop: float) -> str:
    return f"{min(max(seconds / loop * 100, 0), 100):.2f}%"


def poly(points: list[tuple[float, float]]) -> str:
    return "M" + "L".join(f"{num(x)} {num(y)}" for x, y in points)


Box = tuple[float, float, float, float]


# The Earth


@cache
def land_bitmap() -> tuple[bytes, int, int]:
    """Decode the run-length encoded equirectangular land bitmap in land.ts."""
    source = LAND.read_text(encoding="utf-8")
    width = int(re.search(r"LAND_WIDTH = (\d+)", source).group(1))
    height = int(re.search(r"LAND_HEIGHT = (\d+)", source).group(1))
    raw = base64.b64decode(re.search(r'LAND_RLE =\s*"([^"]+)"', source).group(1))
    bits = bytearray(width * height)
    pos = 0
    for row in range(height):
        col = 0
        land = False
        while col < width and pos < len(raw):
            run = raw[pos]
            pos += 1
            if land and run:
                start = row * width + col
                bits[start : start + run] = b"\x01" * run
            col += run
            land = not land
    return bytes(bits), width, height


def is_land(lat: float, lon: float) -> bool:
    bits, width, height = land_bitmap()
    row = min(height - 1, max(0, int((90 - lat) / 180 * height)))
    col = int((lon + 180) / 360 * width) % width
    return bits[row * width + col] == 1


@cache
def lattice() -> tuple[tuple[float, float], ...]:
    """Equal-area land lattice: rings of latitude, alternate rings offset half a step."""
    points = []
    ring = 0
    lat = -90 + STEP / 2
    while lat < 90:
        count = max(1, round(360 * math.cos(math.radians(lat)) / STEP))
        offset = (ring & 1) * 0.5
        for k in range(count):
            lon = -180 + (k + offset) * 360 / count
            if is_land(lat, lon):
                points.append((lat, lon))
        lat += STEP
        ring += 1
    return tuple(points)


class Earth:
    """The dotted Earth at a given radius, turned to `view` and placed so London is at `london`."""

    def __init__(self, radius: float, london: tuple[float, float], view: tuple[float, float]):
        self.radius = radius
        self.lon0 = view[1]
        self.sin0, self.cos0 = math.sin(math.radians(view[0])), math.cos(math.radians(view[0]))
        vx, vy, _ = self.vec(*LONDON)
        self.london = london
        self.cx, self.cy = london[0] - radius * vx, london[1] + radius * vy

    def vec(self, lat: float, lon: float) -> tuple[float, float, float]:
        """Orthographic view; z > 0 faces the viewer."""
        phi, dlon = math.radians(lat), math.radians(lon - self.lon0)
        x = math.cos(phi) * math.sin(dlon)
        y = self.cos0 * math.sin(phi) - self.sin0 * math.cos(phi) * math.cos(dlon)
        z = self.sin0 * math.sin(phi) + self.cos0 * math.cos(phi) * math.cos(dlon)
        return x, y, z

    def screen(self, vec: tuple[float, float, float]) -> tuple[float, float]:
        return self.cx + self.radius * vec[0], self.cy - self.radius * vec[1]

    def dots(self, height: float, hidden: list[Box]) -> str:
        """Land dots in four depth bands, each one path of round-capped stubs. Dots off the
        card or under something opaque are left out."""
        bands: dict[int, list[tuple[float, float]]] = {0: [], 1: [], 2: [], 3: []}
        for lat, lon in lattice():
            vec = self.vec(lat, lon)
            if vec[2] <= 0.02:
                continue
            x, y = self.screen(vec)
            if not (-4 <= x <= WIDTH + 4 and -4 <= y <= height + 4):
                continue
            if any(x0 + 2 <= x <= x1 - 2 and y0 + 2 <= y <= y1 - 2 for x0, y0, x1, y1 in hidden):
                continue
            band = 0 if vec[2] < 0.22 else 1 if vec[2] < 0.42 else 2 if vec[2] < 0.62 else 3
            bands[band].append((x, y))
        style = {0: (0.24, 1.2), 1: (0.42, 1.4), 2: (0.6, 1.55), 3: (0.76, 1.65)}
        paths = []
        for band, points in bands.items():
            if not points:
                continue
            points.sort(key=lambda p: (round(p[1]), p[0]))
            moves = []
            px = py = 0.0
            for x, y in points:
                # "h.01", not "h0": some renderers drop zero-length subpaths.
                moves.append(f"m{num(x - px)} {num(y - py)}h.01")
                px, py = x + 0.01, y
            opacity, width = style[band]
            paths.append(
                f'<path d="M0 0{"".join(moves)}" fill="none" stroke="#D3E4F4" '
                f'stroke-opacity="{opacity}" stroke-width="{width}" stroke-linecap="round" />'
            )
        return "".join(paths)

    def graticule(self) -> str:
        """Meridians every 30 degrees and three parallels, visible face only."""
        paths = []

        def line(points: list[tuple[float, float]]) -> None:
            segments, current = [], []
            for lat, lon in points:
                vec = self.vec(lat, lon)
                if vec[2] > 0:
                    current.append(self.screen(vec))
                elif current:
                    segments.append(current)
                    current = []
            if current:
                segments.append(current)
            paths.extend(poly(s) for s in segments if len(s) > 1)

        for lon in range(-180, 180, 30):
            line([(lat, lon) for lat in range(-84, 85, 3)])
        for lat in (0, 30, 60):
            line([(lat, lon) for lon in range(-180, 181, 3)])
        return (
            f'<path d="{"".join(paths)}" fill="none" stroke="{CYAN_2}" stroke-opacity="0.07" '
            'stroke-width="0.8" />'
        )

    def draw(self, height: float, hidden: list[Box]) -> tuple[list[str], list[str], str]:
        """Defs, elements and CSS: atmosphere, body, land and graticule, rim, and London lit if
        it's on the card."""
        r, cx, cy = self.radius, self.cx, self.cy
        lx, ly = self.london
        rim = r / (r + 70)
        defs = [
            *gradient(
                "radialGradient",
                f'id="atmo" gradientUnits="userSpaceOnUse" cx="{num(cx)}" cy="{num(cy)}" '
                f'r="{num(r + 70)}"',
                [
                    (f"{rim - 0.004:.4f}", CYAN, "0"),
                    (f"{rim:.4f}", CYAN, "0.34"),
                    (f"{rim + 0.03:.4f}", CYAN, "0.1"),
                    ("1", CYAN, "0"),
                ],
            ),
            *gradient(
                "radialGradient",
                f'id="earth" gradientUnits="userSpaceOnUse" cx="{num(cx - 120)}" '
                f'cy="{num(cy - 260)}" r="{num(r + 40)}"',
                [("0", "#0E2036", ""), ("0.62", "#081322", ""), ("0.93", "#0A1B2E", ""),
                 ("1", "#103551", "")],
            ),
            f'    <clipPath id="globeClip"><circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" />'
            "</clipPath>",
        ]
        els = [
            f'    <circle class="rim" cx="{num(cx)}" cy="{num(cy)}" r="{num(r + 70)}" '
            'fill="url(#atmo)" />',
            f'    <circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="url(#earth)" />',
            f'    <g clip-path="url(#globeClip)">{self.graticule()}{self.dots(height, hidden)}</g>',
            f'    <circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="none" stroke="{CYAN}" '
            'stroke-opacity="0.55" stroke-width="1.3" />',
        ]
        css = (
            ".rim{animation:rim 9s ease-in-out infinite}"
            "@keyframes rim{0%,100%{opacity:.75}50%{opacity:1}}"
        )
        if ly - 20 < height:
            defs += gradient(
                "radialGradient",
                'id="londonGlow" cx="0.5" cy="0.5" r="0.5"',
                [("0", AMBER, "0.75"), ("0.35", AMBER, "0.22"), ("1", AMBER, "0")],
            )
            els += [
                f'    <circle cx="{num(lx)}" cy="{num(ly)}" r="20" fill="url(#londonGlow)" />',
                f'    <circle class="lon" cx="{num(lx)}" cy="{num(ly)}" r="3.4" fill="none" '
                f'stroke="{AMBER}" stroke-width="1.1" />',
                f'    <circle class="lon lon2" cx="{num(lx)}" cy="{num(ly)}" r="3.4" fill="none" '
                f'stroke="{AMBER}" stroke-width="1.1" />',
                f'    <circle cx="{num(lx)}" cy="{num(ly)}" r="3.6" fill="{AMBER_2}" />',
            ]
            css += (
                ".lon{transform-box:fill-box;transform-origin:center;opacity:0;"
                "animation:lon 3.6s ease-out infinite}.lon2{animation-delay:-1.8s}"
                "@keyframes lon{0%{opacity:.85;transform:scale(1)}"
                "100%{opacity:0;transform:scale(5.5)}}"
            )
        return defs, els, css


# Ground


def stars(height: float, free: list[Box]) -> list[str]:
    rng = random.Random(STAR_SEED)
    placed, tries = [], 0
    while len(placed) < STARS and tries < STARS * 60:
        tries += 1
        x, y = rng.uniform(8, WIDTH - 8), rng.uniform(8, height - 8)
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in free):
            continue
        radius = rng.choice([0.55, 0.6, 0.7, 0.8, 0.9, 1.0, 1.15])
        placed.append((x, y, radius, rng.uniform(0.18, 0.6)))
    twinkling = "".join(
        f'<circle class="tw tw{i % 4}" cx="{num(x)}" cy="{num(y)}" r="{num(r + 0.25)}" '
        f'fill="#DDF2FF" opacity="{o + 0.25:.2f}" '
        f'style="animation-delay:-{rng.uniform(0, 6):.1f}s" />'
        for i, (x, y, r, o) in enumerate(placed[:TWINKLING])
    )
    plain = "".join(
        f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" opacity="{o:.2f}" />'
        for x, y, r, o in placed[TWINKLING:]
    )
    return [f'    <g fill="#CFE6FF">{plain}</g>', f"    <g>{twinkling}</g>"]


def ground(
    height: float,
    free: list[Box],
    earth: Earth | None = None,
    hidden: list[Box] | None = None,
    glow: Box | None = None,
) -> tuple[list[str], list[str], str]:
    """The card every graphic sits on: the heroes' sky (navy, an indigo nebula top left, a cyan
    one bottom right, seeded stars kept off `free`), then either the Earth or a soft glow behind
    the scene. Returns defs, body and the CSS it animates."""
    defs = [
        *gradient(
            "linearGradient",
            'id="ground" x1="0" y1="0" x2="0.35" y2="1"',
            [("0", "#081020", ""), ("0.55", BG, ""), ("1", "#0B1424", "")],
        ),
        *gradient(
            "radialGradient",
            'id="nebIndigo" cx="0.5" cy="0.5" r="0.5"',
            [("0", "#3B4BB8", "0.32"), ("1", "#3B4BB8", "0")],
        ),
        *gradient(
            "radialGradient",
            'id="nebCyan" cx="0.5" cy="0.5" r="0.5"',
            [("0", "#0A9FE0", "0.34"), ("1", "#0A9FE0", "0")],
        ),
        f'    <clipPath id="frame"><rect x="1" y="1" width="{WIDTH - 2}" height="{num(height - 2)}" '
        'rx="20" /></clipPath>',
    ]
    scene = [
        f'    <rect width="{WIDTH}" height="{num(height)}" fill="url(#ground)" />',
        '    <ellipse cx="190" cy="-30" rx="540" ry="250" fill="url(#nebIndigo)" />',
        f'    <ellipse cx="1040" cy="{num(height)}" rx="580" ry="280" fill="url(#nebCyan)" '
        'opacity="0.55" />',
        *stars(height, free),
    ]
    css = TWINKLE_CSS
    if earth:
        e_defs, e_els, e_css = earth.draw(height, hidden or [])
        defs += e_defs
        scene += e_els
        css += e_css
    if glow:
        x0, y0, x1, y1 = glow
        defs += gradient(
            "radialGradient",
            'id="screenGlow" cx="0.5" cy="0.5" r="0.5"',
            [("0", "#1FA8E8", "0.16"), ("1", "#1FA8E8", "0")],
        )
        scene.append(
            f'    <ellipse cx="{num((x0 + x1) / 2)}" cy="{num((y0 + y1) / 2)}" '
            f'rx="{num((x1 - x0) * 0.75)}" ry="{num((y1 - y0) * 0.85)}" fill="url(#screenGlow)" />'
        )
    body = [
        '  <g clip-path="url(#frame)">',
        *scene,
        "  </g>",
        f'  <rect x="0.75" y="0.75" width="{WIDTH - 1.5}" height="{num(height - 1.5)}" rx="20" '
        'fill="none" stroke="#1A2638" stroke-width="1.5" />',
    ]
    return defs, body, css


def document(
    height: float,
    title: str,
    desc: str,
    defs: list[str],
    css: str,
    body: list[str],
    width: float = WIDTH,
) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {num(width)} {num(height)}" role="img" '
        'aria-labelledby="title desc">',
        f'  <title id="title">{esc(title)}</title>',
        f'  <desc id="desc">{esc(desc)}</desc>',
        "  <defs>",
        "    <style>",
        "      /* Inter and JetBrains Mono, SIL Open Font License 1.1, subset to the glyphs used "
        "here. */",
        "      __FONT_FACES__",
        f"      {FONT_CSS}",
        "      .live{animation:live 2.4s ease-in-out infinite}"
        "@keyframes live{0%,100%{opacity:1}50%{opacity:.35}}",
        f"      {css}",
        "      @media (prefers-reduced-motion: reduce){",
        "        *{animation:none !important}",
        "      }",
        "    </style>",
        *defs,
        "  </defs>",
        *body,
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


# Copy column


def copy_defs() -> list[str]:
    return [
        *gradient(
            "linearGradient",
            'id="nameG" x1="0" y1="0" x2="1" y2="0"',
            [("0", "#FFFFFF", ""), ("1", "#D5E6F5", "")],
        ),
        *gradient(
            "linearGradient",
            'id="roleG" x1="0" y1="0" x2="1" y2="0"',
            [("0", CYAN_2, ""), ("0.55", CYAN, ""), ("1", "#2BA4F0", "")],
        ),
    ]


def pill(
    y: float,
    label: str,
    size: float = 11.5,
    x: float = COPY_X,
    dot: str = GREEN,
    live: bool = True,
) -> list[str]:
    """A mono label in a rounded pill with a dot, pulsing when it's `live`."""
    width = mono_width(len(label), size, 1.5) - 1.5 + 40
    pulse = ' class="live"' if live else ""
    return [
        f'  <rect x="{num(x)}" y="{num(y)}" width="{num(width)}" height="28" rx="14" '
        f'fill="#0E1726" fill-opacity="0.9" stroke="{TERM_EDGE}" />',
        f'  <circle{pulse} cx="{num(x + 16)}" cy="{num(y + 14)}" r="3.4" fill="{dot}" />',
        f'  <text class="mono" x="{num(x + 28)}" y="{num(y + 18.2)}" font-size="{size}" '
        f'letter-spacing="1.5" fill="{INK_2}">{esc(label)}</text>',
    ]


def copy_block(
    label: str, first: str, second: str, lead: list[str], y: float, right: float = COPY_RIGHT
) -> list[str]:
    """The banner's copy treatment a size down: a pill, a one- or two-line heading, a lead."""
    widths = [text_width(first, 40, 800, -1.2), text_width(second, 40, 800, -1.2)]
    widths += [text_width(text, 16) for text in lead]
    if COPY_X + max(widths) > right:
        raise SystemExit(f"'{first}' block runs past the copy column")
    els = [
        *pill(y, label),
        f'  <text class="sans" x="{num(COPY_X - 2)}" y="{num(y + 84)}" font-size="40" '
        f'font-weight="800" letter-spacing="-1.2" fill="url(#nameG)">{esc(first)}</text>',
    ]
    if second:
        els.append(
            f'  <text class="sans" x="{num(COPY_X - 2)}" y="{num(y + 130)}" font-size="40" '
            f'font-weight="800" letter-spacing="-1.2" fill="url(#roleG)">{esc(second)}</text>'
        )
    top = y + (172 if second else 124)
    for i, text in enumerate(lead):
        els.append(
            f'  <text class="sans" x="{num(COPY_X)}" y="{num(top + 24 * i)}" font-size="16" '
            f'fill="{INK_2}">{esc(text)}</text>'
        )
    return els


# Terminal window and typing (the banner's card)


def window(x: float, y: float, w: float, h: float, title: str) -> tuple[list[str], list[str]]:
    """A terminal window: its defs (including the `screen` clip for the body below the title
    bar) and its frame."""
    bar = 36
    defs = [
        *gradient(
            "linearGradient",
            f'id="edge" gradientUnits="userSpaceOnUse" x1="{num(x)}" y1="0" x2="{num(x + w)}" '
            'y2="0"',
            [("0", CYAN, "0"), ("0.2", CYAN, "0.9"), ("0.8", AMBER, "0.9"), ("1", AMBER, "0")],
        ),
        f'    <clipPath id="win"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" '
        f'height="{num(h)}" rx="14" /></clipPath>',
        # Inset from the frame, so a cover stepping right never paints over the window's edge.
        f'    <clipPath id="screen"><rect x="{num(x + 1.5)}" y="{num(y + bar + 1)}" '
        f'width="{num(w - 3)}" height="{num(h - bar - 2.5)}" rx="12.5" /></clipPath>',
        '    <filter id="lift" x="-10%" y="-15%" width="120%" height="140%">'
        '<feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#000" flood-opacity="0.45" />'
        "</filter>",
    ]
    # The shadow is its own layer: run through the filter, the body's colour shifts a shade and
    # the typing covers would show against it.
    els = [
        f'  <rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="14" '
        f'fill="{TERM_BODY}" filter="url(#lift)" />',
        f'  <rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="14" '
        f'fill="{TERM_BODY}" />',
        '  <g clip-path="url(#win)">',
        f'    <rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{bar}" fill="{TERM_BAR}" />',
        f'    <path d="M{num(x)} {num(y + bar + 0.5)}H{num(x + w)}" stroke="{TERM_EDGE}" />',
        f'    <rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="1.5" fill="url(#edge)" />',
        "  </g>",
        f'  <rect x="{num(x + 0.5)}" y="{num(y + 0.5)}" width="{num(w - 1)}" height="{num(h - 1)}" '
        f'rx="13.5" fill="none" stroke="{TERM_EDGE}" />',
    ]
    for i, colour in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        els.append(
            f'  <circle cx="{num(x + 20 + 19 * i)}" cy="{num(y + bar / 2)}" r="5.5" '
            f'fill="{colour}" fill-opacity="0.88" />'
        )
    els.append(
        f'  <text class="mono" x="{num(x + w / 2)}" y="{num(y + bar / 2 + 4)}" '
        f'text-anchor="middle" font-size="11.5" fill="{INK_3}">{esc(title)}</text>'
    )
    return defs, els


def tick(x: float, y: float, cw: float, size: float, colour: str) -> str:
    """A check mark drawn in one mono cell (JetBrains Mono has no U+2713)."""
    return (
        f'<path d="M{num(x + cw * 0.12)} {num(y - size * 0.34)}l{num(cw * 0.28)} '
        f'{num(size * 0.26)} {num(cw * 0.52)} -{num(size * 0.56)}" fill="none" '
        f'stroke="{colour}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />'
    )


def span(text: str, colour: str) -> str:
    return f'<tspan fill="{colour}">{esc(text)}</tspan>'


def session(
    rows: list[tuple],
    x: float,
    y: float,
    size: float,
    line: float,
    inner: float,
    cps: float = 24.0,
    hold: float = 6.5,
) -> tuple[list[str], str]:
    """Lay out a terminal session from its first baseline and give it a typing loop.

    Rows are ("cmd", text), ("out", [(text, colour), ...]), ("ticks", words), ("wait", seconds),
    ("gap", px) and ("idle",). Every element's resting state is the finished session; the
    keyframes hide rows until their turn, step a cover off each command, and clear the screen
    before the loop restarts.
    """
    cw = size * 0.6
    prompt = [("~", INK_3), (" ❯", CYAN)]
    prompt_chars = sum(len(t) for t, _ in prompt) + 1
    t = 0.7
    baseline = y
    placed = []  # (kind, start, typing start, typing end, markup, text x, baseline, chars)
    for row in rows:
        kind = row[0]
        if kind == "gap":
            baseline += row[1]
            continue
        if kind == "wait":
            t += row[1]
            continue
        if kind in ("cmd", "idle"):
            text = row[1] if kind == "cmd" else ""
            if (prompt_chars + len(text)) * cw > inner:
                raise SystemExit(f"'{text}' is wider than the terminal")
            spans = "".join(span(s, c) for s, c in prompt)
            markup = (
                f'<text class="mono" x="{num(x)}" y="{num(baseline)}" font-size="{size}" '
                f'xml:space="preserve">{spans} {span(text, INK)}</text>'
            )
            t0 = t + 0.3
            t1 = t0 + len(text) / cps
            placed.append((kind, t, t0, t1, markup, x + prompt_chars * cw, baseline, len(text)))
            t = t1 + (0.45 if kind == "cmd" else 0)
        elif kind == "out":
            if sum(len(s) for s, _ in row[1]) * cw > inner:
                raise SystemExit("an output line is wider than the terminal")
            markup = (
                f'<text class="mono" x="{num(x)}" y="{num(baseline)}" font-size="{size}" '
                f'xml:space="preserve">{"".join(span(s, c) for s, c in row[1])}</text>'
            )
            placed.append(("out", t, t, t, markup, 0, baseline, 0))
            t += 0.08
        elif kind == "ticks":
            parts, col = [], 0
            for word in row[1]:
                parts.append(tick(x + col * cw, baseline, cw, size, GREEN))
                parts.append(
                    f'<text class="mono" x="{num(x + (col + 2) * cw)}" y="{num(baseline)}" '
                    f'font-size="{size}" fill="{INK}">{esc(word)}</text>'
                )
                col += 2 + len(word) + 2
            if (col - 2) * cw > inner:
                raise SystemExit("the ticks line is wider than the terminal")
            placed.append(("out", t, t, t, "".join(parts), 0, baseline, 0))
            t += 0.08
        baseline += line

    loop = round(t + hold, 1)
    reset = loop - 0.45
    css, els = [], []
    for i, (kind, start, t0, t1, markup, cx, base, n) in enumerate(placed):
        cls = f"r{i}"
        show = pct(start, loop)
        before = pct(max(start - 0.01, 0), loop)
        css.append(
            f".{cls}{{animation:{cls} {loop}s linear infinite}}"
            f"@keyframes {cls}{{0%,{before}{{opacity:0}}{show},{pct(reset, loop)}{{opacity:1}}"
            f"{pct(reset + 0.25, loop)},100%{{opacity:0}}}}"
        )
        inner_els = [markup]
        top = base - size * 1.02
        if kind == "cmd" and n:
            css.append(
                f".{cls}c{{opacity:0;animation:{cls}c {loop}s linear infinite}}"
                f"@keyframes {cls}c{{0%,{pct(t0, loop)}{{opacity:1;transform:translateX(0);"
                f"animation-timing-function:steps({n},end)}}"
                f"{pct(t1, loop)},100%{{opacity:1;transform:translateX({num(n * cw)}px)}}}}"
                f".{cls}k{{opacity:0;animation:{cls}k {loop}s linear infinite}}"
                f"@keyframes {cls}k{{0%,{before}{{opacity:0}}{show},{pct(t1 + 0.4, loop)}"
                f"{{opacity:1}}{pct(t1 + 0.41, loop)},100%{{opacity:0}}}}"
            )
            inner_els.append(
                f'<g class="{cls}c"><rect x="{num(cx)}" y="{num(top)}" width="{num(n * cw + cw)}" '
                f'height="{num(size * 1.32)}" fill="{TERM_BODY}" />'
                f'<rect class="{cls}k" x="{num(cx)}" y="{num(top + 1)}" width="{num(cw)}" '
                f'height="{num(size * 1.22)}" fill="{CYAN}" fill-opacity="0.85" /></g>'
            )
        if kind == "idle":
            frames, s, on = [], start, True
            while s < reset:
                frames.append(f"{pct(s, loop)}{{opacity:{1 if on else 0}}}")
                s += 0.55
                on = not on
            css.append(
                f".{cls}k{{animation:{cls}k {loop}s step-end infinite}}"
                f"@keyframes {cls}k{{0%{{opacity:0}}{''.join(frames)}"
                f"{pct(reset, loop)},100%{{opacity:0}}}}"
            )
            inner_els.append(
                f'<rect class="{cls}k" x="{num(cx)}" y="{num(top + 1)}" width="{num(cw)}" '
                f'height="{num(size * 1.22)}" fill="{CYAN}" fill-opacity="0.85" />'
            )
        els.append(f'<g class="{cls}">{"".join(inner_els)}</g>')
    return els, "".join(css)


# Panels


def panel_defs() -> list[str]:
    return gradient(
        "linearGradient",
        'id="panelEdge" x1="0" y1="0" x2="1" y2="0"',
        [("0", CYAN, "0"), ("0.2", CYAN, "0.75"), ("0.8", AMBER, "0.75"), ("1", AMBER, "0")],
    )


def panel(box: Box) -> str:
    """A card on the ground: translucent navy, a hairline edge, and the banner terminal's
    cyan-to-amber line along the top."""
    x0, y0, x1, y1 = box
    return (
        f'<rect x="{num(x0)}" y="{num(y0)}" width="{num(x1 - x0)}" height="{num(y1 - y0)}" '
        f'rx="14" fill="#0B1322" fill-opacity="0.88" stroke="{TERM_EDGE}" />'
        f'<rect x="{num(x0 + 18)}" y="{num(y0)}" width="{num(x1 - x0 - 36)}" height="1.5" '
        'fill="url(#panelEdge)" />'
    )


def grid(top: float, heights: list[float], cols: int = 3, gap: float = 18.0) -> list[Box]:
    """Boxes for cards laid out in rows across the copy column's width; each row is as tall as
    its tallest card, so neighbours line up."""
    width = (WIDTH - 2 * COPY_X - (cols - 1) * gap) / cols
    boxes, y = [], top
    for start in range(0, len(heights), cols):
        row = max(heights[start : start + cols])
        for k in range(len(heights[start : start + cols])):
            x = COPY_X + k * (width + gap)
            boxes.append((x, y, x + width, y + row))
        y += row + gap
    return boxes


# Icons

# Line icons on a 24px grid, stroked in cyan.
GLYPHS = {
    "pulse": "M2 12h4.5l2.5-6.5 4 13 2.5-6.5H22",
    "cycle": "M19.5 12a7.5 7.5 0 0 1-13.4 4.6M4.5 12a7.5 7.5 0 0 1 13.4-4.6M18.6 3.2v4.6H14"
    "M5.4 20.8v-4.6H10",
    "arrow": "M5 19 18 6M9 5.5h9.5V15",
    "people": "M3.5 20c0-3.2 2.4-5.6 5.5-5.6s5.5 2.4 5.5 5.6M9 11.4a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 "
    "0 0 0 6.4ZM16.5 14.6c2.4.4 4 2.5 4 5.4M15.5 5.3a2.9 2.9 0 0 1 0 5.6",
    "prompt": "M4.5 7 9.5 12l-5 5M12.5 18h7",
    "spark": "M12 3.5c.7 4.4 2.6 6.3 7 7-4.4.7-6.3 2.6-7 7-.7-4.4-2.6-6.3-7-7 4.4-.7 6.3-2.6 7-7Z",
}


def glyph(x: float, y: float, key: str) -> str:
    """A capability icon in a 36px tile with its top-left corner at (x, y)."""
    return (
        f'<rect x="{num(x)}" y="{num(y)}" width="36" height="36" rx="9" fill="#0E1726" '
        f'stroke="{TERM_EDGE}" />'
        f'<path transform="translate({num(x + 6)} {num(y + 6)})" d="{GLYPHS[key]}" fill="none" '
        f'stroke="{CYAN}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />'
    )


GLYPHS.update(
    {
        "layers": "M12 3.5 21 8l-9 4.5L3 8ZM3 12.5l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5",
        "hex": "M12 2.8 20 7.4v9.2l-8 4.6-8-4.6V7.4ZM12 8.6a3.4 3.4 0 1 0 0 6.8 3.4 3.4 0 0 0 0-6.8Z",
        "net": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM3 12h18M12 3c2.6 2.6 3.6 5.6 3.6 9S14.6 18.4 12 21"
        "M12 3C9.4 5.6 8.4 8.6 8.4 12s1 6.4 3.6 9",
        "server": "M4 4.5h16v6H4ZM4 13.5h16v6H4ZM7.5 7.5h.01M7.5 16.5h.01M11 7.5h6M11 16.5h6",
        "ring": "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16ZM12 8.6a3.4 3.4 0 1 0 0 6.8 3.4 3.4 0 0 0 0-6.8Z"
        "M6.4 6.4l3.2 3.2M17.6 6.4l-3.2 3.2M6.4 17.6l3.2-3.2M17.6 17.6l-3.2-3.2",
    }
)


@cache
def icon_paths() -> dict[str, str]:
    return json.loads(ICONS.read_text(encoding="utf-8"))["icons"]


# Project cards

# A card is 600 wide inside an 8px transparent margin, so two side by side at 49% of the
# README's width leave an even gap between and below them.
CARD_W, CARD_H, CARD_M, CARD_PAD = 600.0, 336.0, 8.0, 26.0


def build_project(project: dict) -> str:
    """A project card: category, name and language, two lines on what it does, what it's built
    in and how it ships, and the command that installs it."""
    m, w, h = CARD_M, CARD_W, CARD_H
    left, inner = m + CARD_PAD, w - 2 * CARD_PAD
    accent = project["accent"]
    body = wrap(project["body"], 17, inner)
    if len(body) > 2:
        raise SystemExit(f"{project['name']}: the description runs past two lines")
    for command in project["install"]:
        if mono_width(len(command) + 2, 12.5) > inner - 28:
            raise SystemExit(f"{project['name']}: '{command}' is wider than the card")
    rng = random.Random(project["name"])
    stars = "".join(
        f'<circle cx="{num(rng.uniform(m + 8, m + w - 8))}" cy="{num(rng.uniform(m + 8, m + h - 8))}" '
        f'r="{num(rng.choice([0.55, 0.7, 0.85, 1.0]))}" opacity="{rng.uniform(0.15, 0.5):.2f}" />'
        for _ in range(26)
    )
    label, slug, colour = project["lang"]
    lx, ly = m + w - CARD_PAD - 20, m + 44
    scale = 20 * (1.25 if slug == "go" else 0.95) / 24
    defs = [
        *copy_defs(),
        *gradient(
            "linearGradient",
            'id="ground" x1="0" y1="0" x2="0.35" y2="1"',
            [("0", "#09122A", ""), ("0.6", BG, ""), ("1", "#0B1424", "")],
        ),
        *gradient(
            "radialGradient",
            'id="accentGlow" cx="0.5" cy="0.5" r="0.5"',
            [("0", accent, "0.24"), ("1", accent, "0")],
        ),
        *gradient(
            "linearGradient",
            'id="accentEdge" x1="0" y1="0" x2="1" y2="0"',
            [("0", accent, "0"), ("0.25", accent, "0.9"), ("0.75", accent, "0.9"),
             ("1", accent, "0")],
        ),
        f'    <clipPath id="card"><rect x="{num(m)}" y="{num(m)}" width="{num(w)}" '
        f'height="{num(h)}" rx="18" /></clipPath>',
    ]
    els = [
        '  <g clip-path="url(#card)">',
        f'    <rect x="{num(m)}" y="{num(m)}" width="{num(w)}" height="{num(h)}" fill="url(#ground)" />',
        f'    <ellipse cx="{num(m + w - 60)}" cy="{num(m + 10)}" rx="300" ry="180" '
        'fill="url(#accentGlow)" />',
        f'    <g fill="#CFE6FF">{stars}</g>',
        f'    <rect x="{num(m + 24)}" y="{num(m)}" width="{num(w - 48)}" height="1.5" '
        'fill="url(#accentEdge)" />',
        "  </g>",
        f'  <rect x="{num(m + 0.75)}" y="{num(m + 0.75)}" width="{num(w - 1.5)}" '
        f'height="{num(h - 1.5)}" rx="17.5" fill="none" stroke="#1A2638" stroke-width="1.5" />',
        *pill(m + 28, project["kicker"], x=left, dot=accent, live=False),
        f'  <g><title>{esc(label)}</title><circle cx="{num(lx)}" cy="{num(ly)}" r="20" '
        f'fill="#0C1422" stroke="{colour}" stroke-opacity="0.55" stroke-width="1.2" />'
        f'<path transform="translate({num(lx - 12 * scale)} {num(ly - 12 * scale)}) '
        f'scale({scale:.4f})" d="{icon_paths()[slug]}" fill="{colour}" /></g>',
        f'  <text class="sans" x="{num(left - 1)}" y="{num(m + 110)}" font-size="34" '
        f'font-weight="800" letter-spacing="-1" fill="url(#nameG)">{esc(project["name"])}</text>',
        *[
            f'  <text class="sans" x="{num(left)}" y="{num(m + 146 + 24 * k)}" font-size="17" '
            f'fill="{INK_2}">{esc(line)}</text>'
            for k, line in enumerate(body)
        ],
    ]
    for k, (name, value) in enumerate(project["facts"]):
        y = m + 212 + 24 * k
        if text_width(value, 14.5) > inner - 96:
            raise SystemExit(f"{project['name']}: '{value}' is wider than the card")
        els.append(
            f'  <text class="mono" x="{num(left)}" y="{num(y)}" font-size="10.5" '
            f'letter-spacing="1.4" fill="{INK_3}">{esc(name)}</text>'
            f'<text class="sans" x="{num(left + 96)}" y="{num(y)}" font-size="14.5" '
            f'fill="{INK}">{esc(value)}</text>'
        )
    sy = m + 250
    els.append(
        f'  <rect x="{num(left)}" y="{num(sy)}" width="{num(inner)}" height="60" rx="10" '
        f'fill="{TERM_BODY}" stroke="{TERM_EDGE}" />'
    )
    for k, command in enumerate(project["install"]):
        els.append(
            f'  <text class="mono" x="{num(left + 14)}" y="{num(sy + 25 + 20 * k)}" '
            f'font-size="12.5" xml:space="preserve"><tspan fill="{CYAN}">$</tspan>'
            f'<tspan fill="{INK}"> {esc(command)}</tspan></text>'
        )
    facts = ". ".join(f"{name.capitalize()}: {value}" for name, value in project["facts"])
    install = ", then ".join(project["install"])
    desc = f"{project['kicker'].capitalize()}. {project['body']} {facts}. Install: {install}."
    return document(
        h + 2 * m, project["name"], desc, defs, "", els, width=w + 2 * m
    )


# Banner

PILL = "UK · INFRASTRUCTURE ENGINEERING"
NAME = "Netspeedy"
ROLE = "Infrastructure & platform engineering"
TAGLINE = "Automation, networking and platforms, built from real systems."
FOCUS = ["LINUX", "NETWORK", "ANSIBLE", "KUBERNETES", "GITOPS"]
# Illustrative, not copied output: how a change goes through Netspeedy, with nothing private.
BANNER_SESSION = [
    ("cmd", "git push origin main"),
    ("wait", 0.9),
    ("out", [("validate   ", INK_2), ("ok", GREEN), ("   lint, render, plan", INK_3)]),
    ("out", [("review     ", INK_2), ("ok", GREEN), ("   pull request approved", INK_3)]),
    ("out", [("reconcile  ", INK_2), ("ok", GREEN), ("   argo cd synced, healthy", INK_3)]),
    ("out", [("ansible    ", INK_2), ("ok", GREEN), ("   changed=0  failed=0", INK_3)]),
    ("gap", 8),
    ("wait", 0.3),
    ("ticks", ["source of truth", "reviewed", "recoverable"]),
    ("gap", 6),
    ("idle",),
]


def build_banner() -> str:
    height = 360.0
    for text, size, weight, spacing in (
        (NAME, 68, 800, -2.2),
        (ROLE, 23, 600, -0.3),
        (TAGLINE, 16, 400, 0),
    ):
        if COPY_X + text_width(text, size, weight, spacing) > COPY_RIGHT:
            raise SystemExit(f"'{text}' runs past the copy column")
    size, line, pad = 14.0, 22.0, 22.0
    inner = 49 * size * 0.6 + 0.5  # room for 49 mono cells, wider than any line here
    ww = inner + 2 * pad
    wx, wy, wh = 1140 - ww, 58.0, 36 + 18 + line * 7 + 14 + 18
    w_defs, w_els = window(wx, wy, ww, wh, "~/netspeedy — zsh")
    s_els, s_css = session(BANNER_SESSION, wx + pad, wy + 36 + 18 + size, size, line, inner)
    card = (wx, wy, wx + ww, wy + wh)
    g_defs, g_body, g_css = ground(
        height,
        [(36, 36, 620, 300), (wx - 16, wy - 16, wx + ww + 16, wy + wh + 34)],
        Earth(600, (858, 326), CV_VIEW),
        hidden=[card],
    )
    focus, fx = [], COPY_X
    for i, label in enumerate(FOCUS):
        if i:
            focus.append(f'<circle cx="{num(fx + 9.5)}" cy="278" r="2.2" fill="{AMBER}" />')
            fx += 20
        focus.append(f'<text x="{num(fx)}" y="282">{esc(label)}</text>')
        fx += mono_width(len(label), 12.5, 1.6)
    defs = [
        *g_defs,
        *w_defs,
        *copy_defs(),
        *gradient(
            "linearGradient",
            'id="rule" x1="0" y1="0" x2="1" y2="0"',
            [("0", CYAN, ""), ("1", AMBER, "")],
        ),
    ]
    body = [
        *g_body,
        "",
        "  <!-- Left: name, role and focus -->",
        *pill(54, PILL),
        f'  <text class="sans" x="{num(COPY_X - 3)}" y="150" font-size="68" font-weight="800" '
        f'letter-spacing="-2.2" fill="url(#nameG)">{esc(NAME)}</text>',
        f'  <text class="sans" x="{num(COPY_X)}" y="190" font-size="23" font-weight="600" '
        f'letter-spacing="-0.3" fill="url(#roleG)">{esc(ROLE)}</text>',
        f'  <text class="sans" x="{num(COPY_X)}" y="226" font-size="16" fill="{INK_2}">'
        f"{esc(TAGLINE)}</text>",
        f'  <path d="M{num(COPY_X)} 250.5H{num(COPY_X + text_width(TAGLINE, 16))}" '
        'stroke="#8FA3BF" stroke-opacity="0.18" />',
        f'  <rect x="{num(COPY_X)}" y="249.5" width="72" height="2" rx="1" fill="url(#rule)" />',
        f'  <g class="mono" font-size="12.5" letter-spacing="1.6" fill="{INK_3}">'
        f'{"".join(focus)}</g>',
        "",
        "  <!-- Right: a change going through, start to finish -->",
        *w_els,
        f'  <g clip-path="url(#screen)">{"".join(s_els)}</g>',
    ]
    title = "Netspeedy - infrastructure and platform engineering"
    desc = (
        f"{ROLE}. {TAGLINE} A terminal pushes to main and the change is validated, reviewed, "
        "reconciled by Argo CD and applied by Ansible with nothing failing, above the dotted "
        "Earth with London lit."
    )
    return document(height, title, desc, defs, s_css + g_css, body)


# Projects

# The public projects come from projects.json; adding one there adds its card, its place in the
# README grid, its tile in the signals graphic and one to the tool count.


@cache
def projects() -> list[dict]:
    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))["projects"]
    for project in data:
        project["lang"] = tuple(project["lang"])
        project["facts"] = [tuple(fact) for fact in project["facts"]]
        missing = [slug for slug in [project["lang"][1]] if slug not in icon_paths()]
        if missing:
            raise SystemExit(f"{project['name']}: add the {missing[0]} logo to icons.json")
    return data


def count_word(n: int) -> str:
    words = "zero one two three four five six seven eight nine ten eleven twelve".split()
    return words[n] if n < len(words) else str(n)


# Figures band


def figures() -> list[tuple[str, str]]:
    return [
        ("25+", "YEARS IN PRODUCTION"),
        ("GitOps", "K3S AND ARGO CD"),
        ("Edge", "DNS, BGP, CERTIFICATES"),
        (str(len(projects())), "OPEN-SOURCE TOOLS"),
    ]


def build_highlights() -> str:
    """Four headline facts as a figures row: hairline columns, one large figure each and a
    small label, with no boxes or icons."""
    height = 150.0
    x0, x1 = 64.0, WIDTH - 64.0
    col = (x1 - x0) / 4
    els = []
    for i, (value, label) in enumerate(figures()):
        x = x0 + i * col
        if i:
            els.append(
                f'  <path d="M{num(x)} 34V{num(height - 34)}" stroke="url(#hair)" stroke-width="1" />'
            )
        tx = x + (34 if i else 0)
        if text_width(value, 46, 800, -1.4) > col - 50:
            raise SystemExit(f"'{value}' is too wide for its column")
        if mono_width(len(label), 12, 1.8) > col - 40:
            raise SystemExit(f"'{label}' is too wide for its column")
        fill = "figA" if i % 2 == 0 else "figB"
        els.append(
            f'  <text class="sans" x="{num(tx)}" y="86" font-size="46" font-weight="800" '
            f'letter-spacing="-1.4" fill="url(#{fill})">{esc(value)}</text>'
            f'<rect x="{num(tx + 1)}" y="98" width="28" height="2" rx="1" fill="url(#rule)" />'
            f'<text class="mono" x="{num(tx + 1)}" y="124" font-size="12" letter-spacing="1.8" '
            f'fill="{INK_3}">{esc(label)}</text>'
        )
    box = (40.0, 10.0, WIDTH - 40.0, height - 10)
    g_defs, g_body, g_css = ground(height, [box])
    defs = [
        *g_defs,
        *gradient(
            "linearGradient",
            'id="figA" x1="0" y1="0" x2="1" y2="0"',
            [("0", "#FFFFFF", ""), ("1", "#D5E6F5", "")],
        ),
        *gradient(
            "linearGradient",
            'id="figB" x1="0" y1="0" x2="1" y2="0"',
            [("0", CYAN_2, ""), ("0.6", CYAN, ""), ("1", "#2BA4F0", "")],
        ),
        *gradient(
            "linearGradient", 'id="rule" x1="0" y1="0" x2="1" y2="0"', [("0", CYAN, ""), ("1", AMBER, "")]
        ),
        *gradient(
            "linearGradient",
            f'id="hair" gradientUnits="userSpaceOnUse" x1="0" y1="34" x2="0" y2="{num(height - 34)}"',
            [("0", "#8FA3BF", "0"), ("0.5", "#8FA3BF", "0.35"), ("1", "#8FA3BF", "0")],
        ),
    ]
    desc = "Netspeedy in four figures: " + "; ".join(
        f"{value}, {label.lower()}" for value, label in figures()
    ) + "."
    return document(height, "Netspeedy - figures", desc, defs, g_css, [*g_body, *els])


# Operational signals and engineering focus

FOCUS_AREAS = [
    ("Infrastructure as code", "layers",
     "Hosts, services, routing and runners managed as reviewable desired state, not snowflakes."),
    ("Kubernetes and GitOps", "hex",
     "K3s, Argo CD, platform services and environment overlays where orchestration earns it."),
    ("Automation", "cycle",
     "Ansible, GitHub Actions, scripts and CLIs that take fragile manual steps away."),
    ("Networking and edge", "net",
     "DNS, routing, VPNs, certificates and ingress treated as first-class platform work."),
    ("Service ownership", "server",
     "Self-hosted services run with upgrades, backups and failure handling in mind."),
    ("Recovery discipline", "ring",
     "Backup, rollback, unseal and restore designed in, not improvised during incidents."),
]
# The year the ruler ends on; move it on when the profile is next refreshed.
NOW = 2026.9


def build_signals() -> str:
    """Three of the CV's figures drawn to scale beside the public tools, one tile each in the
    tool's own colour, above the six engineering focus areas as cards."""
    w, loop = 280.0, 7.0
    cells = [(556.0, 54.0), (856.0, 54.0), (556.0, 216.0), (856.0, 216.0)]
    css = ["@keyframes fill{0%{opacity:.12}8%{opacity:1}88%{opacity:1}100%{opacity:.12}}"]
    els, defs = [], []

    def head(x: float, y: float, value: str, label: str) -> str:
        return (
            f'<text class="sans" x="{num(x)}" y="{num(y + 34)}" font-size="36" font-weight="800" '
            f'letter-spacing="-1" fill="{INK}">{esc(value)}</text>'
            f'<text class="mono" x="{num(x)}" y="{num(y + 56)}" font-size="10.5" '
            f'letter-spacing="1.4" fill="{INK_3}">{esc(label)}</text>'
        )

    def field(x: float, y: float, height: float, pattern: str, strips: int, cls: str) -> str:
        """A patterned dot field revealed left to right in strips."""
        sw = w / strips
        css.append(f".{cls}{{animation:fill {loop}s ease-out infinite both}}")
        return "".join(
            f'<rect class="{cls}" x="{num(x + i * sw)}" y="{num(y)}" width="{num(sw)}" '
            f'height="{num(height)}" fill="url(#{pattern})" '
            f'style="animation-delay:{i * 0.08:.2f}s" />'
            for i in range(strips)
        )

    # Years: a ruler from 2000 to now, the era starts in amber.
    x, y = cells[0]
    base = y + 112
    ruler = [
        head(x, y, "25+", "YEARS IN PRODUCTION"),
        f'<path d="M{num(x)} {num(base)}H{num(x + w)}" stroke="{INK_3}" stroke-opacity="0.5" />',
    ]
    for year in range(2000, int(NOW) + 1):
        tx = x + (year - 2000) / (NOW - 2000) * w
        era = year in (2000, 2011, 2024)
        ruler.append(
            f'<path d="M{num(tx)} {num(base)}v-{20 if era else 8}" '
            f'stroke="{AMBER if era else INK_3}" stroke-opacity="{1 if era else 0.6}" '
            f'stroke-width="{1.6 if era else 1}" />'
        )
        if era:
            ruler.append(
                f'<text class="mono" x="{num(tx)}" y="{num(base + 16)}" text-anchor="middle" '
                f'font-size="10" fill="{AMBER}">{year}</text>'
            )
    ruler.append(
        f'<circle class="live" cx="{num(x + w)}" cy="{num(base - 4)}" r="3.4" fill="{GREEN}" />'
        f'<text class="mono" x="{num(x + w)}" y="{num(base - 14)}" text-anchor="middle" '
        f'font-size="10" fill="{GREEN}">NOW</text>'
    )
    els.append("".join(ruler))

    # 2,500 VMs: 100 x 25 dots.
    x, y = cells[1]
    p = w / 100
    defs.append(
        f'    <pattern id="vm" width="{p:.2f}" height="{p:.2f}" patternUnits="userSpaceOnUse" '
        f'x="{num(x)}" y="{num(y + 70)}"><circle cx="{p / 2:.2f}" cy="{p / 2:.2f}" r="0.78" '
        f'fill="{CYAN}" /></pattern>'
    )
    els.append(head(x, y, "2,500", "VMS UNDER AUTOMATION") + field(x, y + 70, p * 25, "vm", 20, "vm"))

    # 300 DNS zones: 50 x 6 dots.
    x, y = cells[2]
    p = w / 50
    defs.append(
        f'    <pattern id="zone" width="{p:.2f}" height="{p:.2f}" patternUnits="userSpaceOnUse" '
        f'x="{num(x)}" y="{num(y + 74)}"><circle cx="{p / 2:.2f}" cy="{p / 2:.2f}" r="1.7" '
        f'fill="{CYAN_2}" /></pattern>'
    )
    els.append(head(x, y, "300+", "DNS ZONES MANAGED") + field(x, y + 74, p * 6, "zone", 10, "zn"))

    # The public tools: one tile each in its own colour, lighting in turn.
    x, y = cells[3]
    tools = projects()
    tiles = [head(x, y, str(len(tools)), "PUBLIC TOOLS")]
    gap = 8.0
    tw = min(40.0, (w - gap * (len(tools) - 1)) / len(tools))
    for i, project in enumerate(tools):
        tx = x + i * (tw + gap)
        accent = project["accent"]
        tiles.append(
            f'<g class="tl" style="animation-delay:{i * 0.3:.2f}s"><title>{esc(project["name"])}</title>'
            f'<rect x="{num(tx)}" y="{num(y + 74)}" width="{num(tw)}" height="{num(tw)}" rx="8" '
            f'fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="0.75" />'
            f'<circle cx="{num(tx + tw / 2)}" cy="{num(y + 74 + tw / 2)}" r="{num(min(5, tw / 8))}" '
            f'fill="{accent}" /></g>'
        )
    css.append(f".tl{{animation:fill {loop}s ease-out infinite both}}")
    els.append("".join(tiles))

    # The engineering focus areas, as cards under the figures.
    top = 372.0
    width = (WIDTH - 2 * COPY_X - 2 * 18) / 3
    bodies = [wrap(body, 15, width - 44) for _, _, body in FOCUS_AREAS]
    boxes = grid(top, [86 + 22 * (len(lines) - 1) + 26 for lines in bodies])
    cards = []
    for (title, icon, _), lines, box in zip(FOCUS_AREAS, bodies, boxes):
        x0, y0 = box[0], box[1]
        cards.append(
            panel(box)
            + glyph(x0 + 22, y0 + 22, icon)
            + f'<text class="sans" x="{num(x0 + 72)}" y="{num(y0 + 46)}" font-size="19" '
            f'font-weight="700" fill="{INK}">{esc(title)}</text>'
            + "".join(
                f'<text class="sans" x="{num(x0 + 22)}" y="{num(y0 + 86 + 22 * k)}" '
                f'font-size="15" fill="{INK_2}">{esc(line)}</text>'
                for k, line in enumerate(lines)
            )
        )
    height = boxes[-1][3] + 40
    stats_box = (536.0, 40.0, 1150.0, 350.0)
    g_defs, g_body, g_css = ground(
        height, [(36, 40, 520, 320), stats_box, (40, top - 10, 1160, height - 20)], glow=stats_box
    )
    body = [
        *g_body,
        *copy_block(
            "OPERATIONAL SIGNALS",
            "Production habits,",
            "at every layer.",
            ["Twenty-five years of ISP, media, build and", "platform work behind every repository."],
            72,
        ),
        f'  <path d="M{num(cells[0][0] - 20)} 196H1136" stroke="#8FA3BF" stroke-opacity="0.12" />',
        f'  <path d="M{num(cells[1][0] - 10)} 50V340" stroke="#8FA3BF" stroke-opacity="0.12" />',
        *[f"  {e}" for e in els],
        *[f"  {c}" for c in cards],
    ]
    areas = "; ".join(f"{t}: {b}" for t, _, b in FOCUS_AREAS)
    desc = (
        "Operational signals: 25+ years in production, 2,500 VMs under automation, 300+ DNS "
        f"zones managed and {len(tools)} public tools. Engineering focus. {areas}"
    )
    defs = [*g_defs, *copy_defs(), *panel_defs(), *defs]
    return document(height, "Netspeedy - operational signals", desc, defs, "".join(css) + g_css, body)


# How we work

PRINCIPLES = [
    ("Source of truth first.", "SOURCE",
     "M7 4v11.5M7 15.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5ZM17 4.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 "
     "0-5ZM17 9.5c0 4.2-4.4 4.6-10 6"),
    ("Automate the repeatable.", "AUTOMATE", GLYPHS["cycle"]),
    ("Keep changes reviewable.", "REVIEW",
     "M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6ZM12 9.4a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 "
     "0-5.2Z"),
    ("Design for recovery.", "RECOVER", GLYPHS["ring"]),
    ("Document the surprising.", "DOCUMENT", "M6.5 3h7.5l4 4v14h-11.5ZM14 3v4h4M9.5 12h5M9.5 16h5"),
    ("Communicate clearly.", "EXPLAIN", "M4 5h16v11H10l-4.5 3.5V16H4Z"),
]


def build_how_we_work() -> str:
    """The six principles as stages on one pipeline, a signal ringing each as it passes."""
    height, loop, travel = 440.0, 8.0, 5.0
    x0, x1, ty = 80.0, WIDTH - 80.0, 266.0
    n = len(PRINCIPLES)
    xs = [x0 + 60 + i * (x1 - x0 - 120) / (n - 1) for i in range(n)]
    length = x1 - x0
    lead = "Making change understandable, repeatable and safe to maintain."

    def icon(cx: float, cy: float, d: str, size: float) -> str:
        s = size / 24
        return (
            f'<path transform="translate({num(cx - 12 * s)} {num(cy - 12 * s)}) scale({s:.3f})" '
            f'd="{d}" fill="none" stroke="{CYAN}" stroke-width="{1.7 / s:.2f}" '
            'stroke-linecap="round" stroke-linejoin="round" />'
        )

    els = [
        *pill(44, "HOW WE WORK"),
        f'  <text class="sans" x="{num(COPY_X)}" y="124" font-size="40" font-weight="800" '
        'letter-spacing="-1.2"><tspan fill="url(#nameG)">Six habits, </tspan>'
        '<tspan fill="url(#roleG)">one pipeline.</tspan></text>',
        f'  <text class="sans" x="{num(COPY_X)}" y="162" font-size="16" fill="{INK_2}">'
        f"{esc(lead)}</text>",
        f'  <path d="M{num(x0)} {num(ty)}H{num(x1)}" stroke="url(#track)" stroke-width="1.6" '
        'stroke-opacity="0.6" />',
        f'  <path class="trip" d="M{num(x0)} {num(ty)}H{num(x1)}" stroke="{CYAN_2}" '
        f'stroke-width="3" stroke-linecap="round" stroke-dasharray="26 {num(length + 26)}" '
        f'stroke-dashoffset="{num(-length * 0.55)}" />',
    ]
    arrive = travel / loop * 100
    css = [
        f".trip{{animation:trip {loop}s linear infinite}}"
        f"@keyframes trip{{0%{{stroke-dashoffset:26;opacity:1}}{arrive:.1f}%{{stroke-dashoffset:"
        f"{num(-length)};opacity:1}}{arrive + 0.1:.1f}%,100%{{stroke-dashoffset:{num(-length)};"
        "opacity:0}}",
        ".ring{opacity:0;transform-box:fill-box;transform-origin:center;"
        f"animation:ring {loop}s ease-out infinite}}"
        "@keyframes ring{0%{opacity:.85;transform:scale(1)}18%{opacity:0;transform:scale(1.7)}"
        "100%{opacity:0}}",
    ]
    for x, (line, word, d) in zip(xs, PRINCIPLES):
        when = (x - x0) / length * travel
        lines = wrap(line, 16, 150, 600)
        els.append(
            f'  <circle cx="{num(x)}" cy="{num(ty)}" r="44" fill="url(#nodeGlow)" />'
            f'<circle class="ring" cx="{num(x)}" cy="{num(ty)}" r="28" fill="none" stroke="{CYAN}" '
            f'stroke-width="1.2" style="animation-delay:{when:.2f}s" />'
            f'<circle cx="{num(x)}" cy="{num(ty)}" r="28" fill="#0E1726" stroke="{TERM_EDGE}" '
            'stroke-width="1.4" />'
            + icon(x, ty, d, 28)
            + f'<text class="mono" x="{num(x)}" y="{num(ty - 46)}" text-anchor="middle" '
            f'font-size="11" letter-spacing="1.6" fill="{CYAN_2}">{word}</text>'
            + "".join(
                f'<text class="sans" x="{num(x)}" y="{num(ty + 60 + 21 * k)}" text-anchor="middle" '
                f'font-size="16" font-weight="600" fill="{INK}">{esc(t)}</text>'
                for k, t in enumerate(lines)
            )
        )
    els.append(
        f'  <text class="mono" x="{num(WIDTH / 2)}" y="404" font-size="12.5" text-anchor="middle" '
        f'xml:space="preserve"><tspan fill="{INK_3}">principles : </tspan>'
        f'<tspan fill="{GREEN}">ok={n}</tspan><tspan fill="{INK_3}">  changed=0  failed=0</tspan>'
        "</text>"
    )
    box = (50.0, 190.0, WIDTH - 50.0, 380.0)
    g_defs, g_body, g_css = ground(height, [(36, 30, 760, 180), box], glow=box)
    defs = [
        *g_defs,
        *copy_defs(),
        *gradient(
            "linearGradient",
            f'id="track" gradientUnits="userSpaceOnUse" x1="{num(x0)}" y1="0" x2="{num(x1)}" y2="0"',
            [("0", CYAN, "0"), ("0.15", CYAN, ""), ("0.85", AMBER, ""), ("1", AMBER, "0")],
        ),
        *gradient(
            "radialGradient",
            'id="nodeGlow" cx="0.5" cy="0.5" r="0.5"',
            [("0", CYAN, "0.22"), ("1", CYAN, "0")],
        ),
    ]
    desc = "How we work: six habits, one pipeline. " + " ".join(p[0] for p in PRINCIPLES)
    return document(height, "Netspeedy - how we work", desc, defs, "".join(css) + g_css, [*g_body, *els])


# Site and link cards: the project card's style for KuberTech and the maintainer's links.

SITES = [
    {
        "name": "kubertech.io",
        "kicker": "PRODUCTION PLATFORM",
        "accent": "#4BD8FF",
        "body": "The public production view of the GitOps platform: real services, controlled "
        "change and practical infrastructure automation.",
        "facts": [("RUNS ON", "K3s, reconciled by Argo CD"), ("ROLE", "Production public view"),
                  ("PART OF", "Netspeedy, as its Kubernetes and GitOps slice")],
    },
    {
        "name": "kubertech.dev",
        "kicker": "DEVELOPMENT PLATFORM",
        "accent": "#F5B841",
        "body": "The development side of the same platform, where GitOps changes are proven "
        "behind production-style guardrails before release.",
        "facts": [("RUNS ON", "K3s, reconciled by Argo CD"), ("ROLE", "Development and validation"),
                  ("PROMOTES TO", "kubertech.io, once a change is proven")],
    },
]
LINKS = [
    {"name": "oakes.me.uk", "file": "link-oakes", "kicker": "PUBLIC CV", "accent": "#1FC7FF",
     "mark": "prompt", "body": "Simon Oakes' CV and professional profile."},
    {"name": "github.com/soakes", "file": "link-github", "kicker": "MORE PUBLIC WORK",
     "accent": "#F5B841", "mark": "github", "body": "Personal tools and projects, outside the org."},
]


def card_frame(
    height: float,
    accent: str,
    seed: str,
    stars: int,
    glow: tuple[float, float, str] = (300, 180, "0.24"),
) -> tuple[list[str], list[str]]:
    """The project card's ground, glow, accent edge and outline, at a given height."""
    m, w = CARD_M, CARD_W
    rng = random.Random(seed)
    dots = "".join(
        f'<circle cx="{num(rng.uniform(m + 8, m + w - 8))}" '
        f'cy="{num(rng.uniform(m + 8, m + height - 8))}" '
        f'r="{num(rng.choice([0.55, 0.7, 0.85, 1.0]))}" opacity="{rng.uniform(0.15, 0.5):.2f}" />'
        for _ in range(stars)
    )
    defs = [
        *copy_defs(),
        *gradient(
            "linearGradient",
            'id="ground" x1="0" y1="0" x2="0.35" y2="1"',
            [("0", "#09122A", ""), ("0.6", BG, ""), ("1", "#0B1424", "")],
        ),
        *gradient(
            "radialGradient",
            'id="accentGlow" cx="0.5" cy="0.5" r="0.5"',
            [("0", accent, glow[2]), ("1", accent, "0")],
        ),
        *gradient(
            "linearGradient",
            'id="accentEdge" x1="0" y1="0" x2="1" y2="0"',
            [("0", accent, "0"), ("0.25", accent, "0.9"), ("0.75", accent, "0.9"),
             ("1", accent, "0")],
        ),
        f'    <clipPath id="card"><rect x="{num(m)}" y="{num(m)}" width="{num(w)}" '
        f'height="{num(height)}" rx="18" /></clipPath>',
    ]
    els = [
        '  <g clip-path="url(#card)">',
        f'    <rect x="{num(m)}" y="{num(m)}" width="{num(w)}" height="{num(height)}" '
        'fill="url(#ground)" />',
        f'    <ellipse cx="{num(m + w - 60)}" cy="{num(m + 10)}" rx="{num(glow[0])}" '
        f'ry="{num(glow[1])}" fill="url(#accentGlow)" />',
        *([f'    <g fill="#CFE6FF">{dots}</g>'] if stars else []),
        f'    <rect x="{num(m + 24)}" y="{num(m)}" width="{num(w - 48)}" height="1.5" '
        'fill="url(#accentEdge)" />',
        "  </g>",
        f'  <rect x="{num(m + 0.75)}" y="{num(m + 0.75)}" width="{num(w - 1.5)}" '
        f'height="{num(height - 1.5)}" rx="17.5" fill="none" stroke="#1A2638" stroke-width="1.5" />',
    ]
    return defs, els


def build_site(site: dict) -> str:
    m, w, h, pad = CARD_M, CARD_W, 298.0, CARD_PAD
    left, inner = m + pad, w - 2 * pad
    body = wrap(site["body"], 17, inner)
    if len(body) > 2:
        raise SystemExit(f"{site['name']}: the description runs past two lines")
    defs, els = card_frame(h, site["accent"], site["name"], 22)
    lx, ly, scale = m + w - pad - 20, m + 44, 20 * 0.95 / 24
    els += [
        *pill(m + 28, site["kicker"], x=left, dot=site["accent"], live=False),
        f'  <g><title>Kubernetes</title><circle cx="{num(lx)}" cy="{num(ly)}" r="20" '
        'fill="#0C1422" stroke="#5a8ff0" stroke-opacity="0.55" stroke-width="1.2" />'
        f'<path transform="translate({num(lx - 12 * scale)} {num(ly - 12 * scale)}) '
        f'scale({scale:.4f})" d="{icon_paths()["kubernetes"]}" fill="#5a8ff0" /></g>',
        f'  <text class="sans" x="{num(left - 1)}" y="{num(m + 110)}" font-size="34" '
        f'font-weight="800" letter-spacing="-1" fill="url(#nameG)">{esc(site["name"])}</text>',
        *[
            f'  <text class="sans" x="{num(left)}" y="{num(m + 146 + 24 * k)}" font-size="17" '
            f'fill="{INK_2}">{esc(line)}</text>'
            for k, line in enumerate(body)
        ],
    ]
    for k, (name, value) in enumerate(site["facts"]):
        if text_width(value, 14.5) > inner - 110:
            raise SystemExit(f"{site['name']}: '{value}' is wider than the card")
        y = m + 212 + 24 * k
        els.append(
            f'  <text class="mono" x="{num(left)}" y="{num(y)}" font-size="10.5" '
            f'letter-spacing="1.4" fill="{INK_3}">{esc(name)}</text>'
            f'<text class="sans" x="{num(left + 110)}" y="{num(y)}" font-size="14.5" '
            f'fill="{INK}">{esc(value)}</text>'
        )
    facts = ". ".join(f"{n.capitalize()}: {v}" for n, v in site["facts"])
    desc = f"{site['kicker'].capitalize()}. {site['body']} {facts}."
    return document(h + 2 * m, site["name"], desc, defs, "", els, width=w + 2 * m)


def build_link(link: dict) -> str:
    m, w, h, pad = CARD_M, CARD_W, 150.0, CARD_PAD
    left = m + pad
    if text_width(link["body"], 16.5) > w - 2 * pad - 70:
        raise SystemExit(f"{link['name']}: the description is wider than the card")
    defs, els = card_frame(h, link["accent"], link["name"], 0, (260, 140, "0.22"))
    cx, cy = m + w - pad - 26, m + h / 2
    if link["mark"] == "github":
        mark = (
            f'<path transform="translate({num(cx - 12)} {num(cy - 12)})" '
            f'd="{icon_paths()["github"]}" fill="{INK}" />'
        )
    else:
        # The >_ mark from the cv hero and oakes.me.uk.
        mark = (
            f'<path d="M{num(cx - 9)} {num(cy - 7)}l6.5 7-6.5 7" fill="none" stroke="#1FC7FF" '
            'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />'
            f'<path d="M{num(cx + 1)} {num(cy + 7)}h8" fill="none" stroke="#FCBB39" '
            'stroke-width="2.6" stroke-linecap="round" />'
        )
    els += [
        *pill(m + 24, link["kicker"], x=left, dot=link["accent"], live=False),
        f'  <text class="sans" x="{num(left - 1)}" y="{num(m + 94)}" font-size="28" '
        f'font-weight="800" letter-spacing="-0.8" fill="url(#nameG)">{esc(link["name"])}</text>',
        f'  <text class="sans" x="{num(left)}" y="{num(m + 124)}" font-size="16.5" '
        f'fill="{INK_2}">{esc(link["body"])}</text>',
        f'  <circle cx="{num(cx)}" cy="{num(cy)}" r="26" fill="#0C1422" stroke="{link["accent"]}" '
        'stroke-opacity="0.55" stroke-width="1.2" />',
        "  " + mark,
    ]
    return document(h + 2 * m, link["name"], f"{link['name']}: {link['body']}", defs, "", els,
                    width=w + 2 * m)


# Social preview

SOCIAL = (1280, 640)


def build_social(banner: str) -> str:
    """The repository's social preview: the banner, frozen at its rest frame, on a 1280x640
    card with the org's address underneath."""
    width, height = SOCIAL
    inner = banner.replace("<svg ", '<svg x="40" y="118" width="1200" height="360" ', 1)
    # Frozen at the rest frame, whatever the renderer's motion setting.
    inner = inner.replace(
        "@media (prefers-reduced-motion: reduce){",
        "*{animation:none !important}\n      @media (prefers-reduced-motion: reduce){",
        1,
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-labelledby="sTitle">\n'
        '  <title id="sTitle">Netspeedy on GitHub</title>\n'
        f'  <rect width="{width}" height="{height}" fill="{BG}" />\n'
        f"{inner}"
        f'  <text class="mono" x="{width / 2:g}" y="560" text-anchor="middle" font-size="22" '
        f'letter-spacing="2" fill="{INK_3}">github.com/netspeedy</text>\n'
        "</svg>\n"
    )


def render_png(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    """Screenshot the card in headless Chrome, which renders the embedded fonts exactly."""
    chrome = os.environ.get("CHROME") or next(
        (c for c in CHROME_CANDIDATES if Path(c).exists() or shutil.which(c)), None
    )
    if not chrome:
        raise SystemExit("the social preview needs Chrome or Chromium to render; set CHROME")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-prefers-reduced-motion",
                # Time for the embedded fonts to load before the shot.
                "--virtual-time-budget=5000",
                f"--user-data-dir={profile}",
                f"--window-size={width},{height}",
                f"--screenshot={png_path}",
                svg_path.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
        )


# The README's project grid

START, END = "<!-- projects:start -->", "<!-- projects:end -->"


def readme_block() -> str:
    """Selected Public Work's grid: a card per project linking to its repository, then a badge
    per Homebrew tap."""
    cards = []
    for project in projects():
        facts = "; ".join(f"{name.lower()} {value}" for name, value in project["facts"])
        alt = (
            f"{project['name']}: {project['kicker'].capitalize()}. {project['body']} {facts}. "
            f"Install: {', then '.join(project['install'])}."
        )
        cards.append(
            f'  <a href="https://github.com/{project["repo"]}"><img '
            f'src="./assets/project-{project["name"]}.svg" width="49%" '
            f'alt="{html.escape(alt, quote=True)}" /></a>'
        )
    lines = [START, '<p align="center">', *cards, "</p>"]
    taps = [project["tap"] for project in projects() if project.get("tap")]
    if taps:
        badges = []
        for tap in taps:
            name = tap.split("/")[1]
            badges.append(
                f"[![{name}](https://img.shields.io/badge/{name.replace('-', '--')}-FBB040"
                f"?style=for-the-badge&logo=homebrew&logoColor=black)](https://github.com/{tap})"
            )
        lines += ["", '<div align="center">', "",
                  "Each card opens its repository. Homebrew taps for the tools above:", "",
                  *badges, "", "</div>"]
    return "\n".join([*lines, END])


def update_readme(check: bool) -> bool:
    """Rewrite the project grid in profile/README.md; with check, only report whether it's
    current."""
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"profile/README.md needs the {START} and {END} markers")
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    updated = head + readme_block() + tail
    if check:
        return updated == text
    README.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="fail if any graphic or the README grid is out of date")
    args = parser.parse_args()
    banner = build_banner()
    graphics = [
        ("netspeedy-banner.svg", lambda: banner),
        ("netspeedy-highlights.svg", build_highlights),
        ("netspeedy-signals.svg", build_signals),
        ("netspeedy-how-we-work.svg", build_how_we_work),
    ]
    for project in projects():
        graphics.append((f"project-{project['name']}.svg", lambda p=project: build_project(p)))
    for site in SITES:
        graphics.append((f"site-{site['name'].replace('.', '-')}.svg", lambda s=site: build_site(s)))
    for link in LINKS:
        graphics.append((f"{link['file']}.svg", lambda k=link: build_link(k)))
    graphics.append(("social-preview.svg", lambda: build_social(banner)))
    stale = []
    for name, build in graphics:
        svg = build()
        svg = svg.replace("__FONT_FACES__", font_faces(svg))
        # Only references count; a card may show a URL as text in its install command.
        if re.search(r'(?:href|src)="(?:https?:)?//|url\((?:["\']?)(?:https?:)?//', svg):
            raise SystemExit(f"external reference found in {name}")
        ET.fromstring(svg)  # well-formed, or this raises
        path = ASSETS / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != svg:
                stale.append(name)
            continue
        path.write_text(svg, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)} ({len(svg.encode()) / 1024:.1f} KiB)")
    if args.check:
        if not update_readme(check=True):
            stale.append("profile/README.md")
        if stale:
            raise SystemExit("Out of date, run `make readme-graphics`: " + ", ".join(stale))
        print("Graphics and README grid are current.")
        return
    update_readme(check=False)
    print("Updated the project grid in profile/README.md")
    social = ASSETS / "social-preview.svg"
    render_png(social, social.with_suffix(".png"), *SOCIAL)
    print(f"Wrote {social.with_suffix('.png').relative_to(ROOT)} ({SOCIAL[0]}x{SOCIAL[1]})")


if __name__ == "__main__":
    main()
