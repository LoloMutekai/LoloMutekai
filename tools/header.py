"""Generate the profile header SVGs (dark and light) with all text as outlines.

Text is converted to paths so the banner looks the same on every machine:
GitHub serves README SVGs as images, which cannot load web fonts. The terminal
lines are copied from a real run of kairo-alcove/reference/check.py; rerun it
and update TERMINAL if the checker's output changes.

    python3 tools/header.py --fonts /usr/share/fonts

Fonts (outlines only): P052 Italic (URW base35), JetBrains Mono and
Clarity City (SIL OFL).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

WIDTH, HEIGHT = 1200, 320
FONT_FILES = {
    "serif_italic": "gsfonts/P052-Italic.otf",
    "mono": "TTF/JetBrainsMono-Regular.ttf",
    "mono_italic": "TTF/JetBrainsMono-Italic.ttf",
    "sans": "~/.local/share/fonts/clarity-city/ClarityCity-Regular.ttf",
}
THEMES = {
    "dark": dict(bg="#0d0e12", edge="#2a2730", wave="#8a93a6", wave_op=".07", label="#8f8798",
                 rose="#c98ba0", sub="#b4acbc", card="#16131a", card_edge="#2a2730", text="#f2e8ed",
                 muted="#8f8798", ok="#9fd3b5", bad="#e08a9b", spark="#f2c4d3"),
    "light": dict(bg="#fbf6f8", edge="#eadde3", wave="#a8566f", wave_op=".08", label="#6f6577",
                  rose="#a8566f", sub="#5d5466", card="#ffffff", card_edge="#eadde3", text="#1f1a24",
                  muted="#6f6577", ok="#2f7d57", bad="#b4405c", spark="#c98ba0"),
}
# (prompt?, [(text, colour_key, italic?)]) — copied from a real run, 2026-10-19.
TERMINAL = [
    (True, [("python3 reference/check.py", "text", False)]),
    (False, [('  "reachable_states": ', "muted", False), ("40", "rose", False), (",", "muted", False)]),
    (False, [('  "status": ', "muted", False), ('"PASS"', "ok", False), (",", "muted", False)]),
    (True, [("python3 reference/check.py --variant leaky", "text", False)]),
    (False, [('  "status": ', "muted", False), ('"FAIL"', "bad", False), (",", "muted", False),
             ("  ← as it should", "muted", True)]),
]


class Face:
    """One font file, able to turn a string into outline paths."""

    def __init__(self, path: Path) -> None:
        self.font = TTFont(str(path))
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def paths(self, text: str, x: float, y: float, size: float, fill: str,
              tracking: float = 0.0) -> tuple[str, float]:
        scale = size / self.upm
        parts, cursor = [], 0.0
        for char in text:
            name = self.cmap.get(ord(char))
            if name is None:
                raise ValueError(f"glyph missing for {char!r}")
            pen = SVGPathPen(self.glyphs)
            self.glyphs[name].draw(pen)
            d = pen.getCommands()
            if d:
                parts.append(f'<path transform="translate({cursor:.1f} 0)" d="{d}"/>')
            cursor += self.glyphs[name].width + tracking / scale
        group = (f'<g fill="{fill}" transform="translate({x:.2f} {y:.2f}) scale({scale:.5f} {-scale:.5f})">'
                 + "".join(parts) + "</g>")
        return group, cursor * scale


def waves(colour: str, opacity: str) -> str:
    lines = []
    for i in range(12):
        points = []
        for step in range(0, WIDTH + 1, 20):
            t = step / WIDTH
            y = 40 + i * 22 + 26 * math.sin(2 * math.pi * (t * 0.9 + i * 0.07)) + 10 * math.sin(6 * t + i)
            points.append(f"{step},{y:.1f}")
        lines.append(f'<polyline points="{" ".join(points)}"/>')
    return (f'<g fill="none" stroke="{colour}" stroke-opacity="{opacity}" stroke-width=".7" '
            f'aria-hidden="true">{"".join(lines)}</g>')


def bow(cx: float, cy: float, scale: float, colour: str) -> str:
    loops = ("M0,0 C-5,-11 -21,-13 -21,-3 C-21,8 -6,6 0,0 Z "
             "M0,0 C5,-11 21,-13 21,-3 C21,8 6,6 0,0 Z")
    tails = ("M-1.5,2 C-4,8 -7,13 -10,17 L-5.5,15.5 L-4.5,19.5 C-2.5,13 -0.5,7 0,3 Z "
             "M1.5,2 C4,8 7,13 10,17 L5.5,15.5 L4.5,19.5 C2.5,13 0.5,7 0,3 Z")
    # Position lives on the outer group: a CSS animation on an element replaces
    # its transform attribute, so the swaying group must carry no placement.
    return (f'<g transform="translate({cx} {cy}) scale({scale})"><g class="bow">'
            f'<path d="{loops}" fill="{colour}" fill-opacity=".22" stroke="{colour}" stroke-width="1.6" '
            f'stroke-linejoin="round"/><path d="{tails}" fill="{colour}" fill-opacity=".22" '
            f'stroke="{colour}" stroke-width="1.4" stroke-linejoin="round"/>'
            f'<ellipse cx="0" cy="-0.5" rx="3.4" ry="3.9" fill="{colour}"/></g></g>')


def sparkle(cx: float, cy: float, r: float, colour: str, delay: float) -> str:
    d = (f"M{cx},{cy - r} Q{cx},{cy} {cx + r},{cy} Q{cx},{cy} {cx},{cy + r} "
         f"Q{cx},{cy} {cx - r},{cy} Q{cx},{cy} {cx},{cy - r} Z")
    return f'<path class="twinkle" style="animation-delay:{delay}s" d="{d}" fill="{colour}"/>'


def heart(x: float, y: float, colour: str) -> str:
    d = "M0,3 C0,0 -5,0 -5,3.5 C-5,6.5 0,9 0,10.5 C0,9 5,6.5 5,3.5 C5,0 0,0 0,3 Z"
    return f'<path transform="translate({x} {y}) scale(1.05)" d="{d}" fill="{colour}"/>'


STYLE = """<style>
.twinkle{animation:tw 3.4s ease-in-out infinite}
.cursor{animation:blink 1.1s steps(1) infinite}
.bow{transform-box:fill-box;transform-origin:50% 30%;animation:sway 7s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.2}50%{opacity:1}}
@keyframes blink{50%{opacity:0}}
@keyframes sway{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@media (prefers-reduced-motion:reduce){.twinkle,.cursor,.bow{animation:none}}
</style>"""


def build(theme: dict[str, str], faces: dict[str, Face]) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
           f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="t d">',
           '<title id="t">Lolo</title>',
           '<desc id="d">Lolo, in dusty rose italic, with a small bow. Beside it, a terminal runs the '
           'public notebook\'s checker: 40 reachable states, PASS; the deliberately leaky variant FAILs.</desc>',
           STYLE,
           f'<rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="22" fill="{theme["bg"]}" '
           f'stroke="{theme["edge"]}"/>',
           waves(theme["wave"], theme["wave_op"])]
    label, _ = faces["mono"].paths("LOLOMUTEKAI · KAIRO", 66, 80, 14, theme["label"], tracking=3.6)
    word, word_w = faces["serif_italic"].paths("Lolo", 58, 196, 124, theme["rose"])
    sub, _ = faces["sans"].paths("agents with private memory, living on my laptop", 66, 246, 21, theme["sub"])
    out += [label, word, sub, bow(58 + word_w + 30, 120, 1.25, theme["rose"])]
    out += [sparkle(58 + word_w + 78, 150, 7, theme["spark"], 0.0),
            sparkle(40, 120, 5, theme["spark"], 1.1), sparkle(560, 70, 6, theme["spark"], 2.0),
            sparkle(590, 262, 4.5, theme["spark"], 0.6)]
    # Terminal card.
    cx, cy, cw, ch = 646, 52, 500, 216
    out.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="14" fill="{theme["card"]}" '
               f'stroke="{theme["card_edge"]}"/>')
    out.append(f'<line x1="{cx}" y1="{cy + 34}" x2="{cx + cw}" y2="{cy + 34}" stroke="{theme["card_edge"]}"/>')
    title, _ = faces["mono"].paths("~/kairo-alcove", cx + 46, cy + 23, 13, theme["muted"])
    out += [bow(cx + 24, cy + 17, 0.55, theme["rose"]), title]
    line_y = cy + 66
    for prompt, spans in TERMINAL:
        x = cx + 22
        if prompt:
            out.append(heart(x + 4, line_y - 11, theme["rose"]))
            x += 20
        for text, colour, italic in spans:
            face = faces["mono_italic"] if italic else faces["mono"]
            group, width = face.paths(text, x, line_y, 15.5, theme[colour])
            out.append(group)
            x += width
        line_y += 28
    out.append(heart(cx + 26, line_y - 11, theme["rose"]))
    out.append(f'<rect class="cursor" x="{cx + 42}" y="{line_y - 14}" width="8.5" height="17" rx="1.5" '
               f'fill="{theme["rose"]}"/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", default="/usr/share/fonts")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets"))
    args = parser.parse_args()
    faces = {}
    for key, rel in FONT_FILES.items():
        path = Path(rel).expanduser() if rel.startswith("~") else Path(args.fonts) / rel
        faces[key] = Face(path)
    for name, theme in THEMES.items():
        Path(args.out, f"header-{name}.svg").write_text(build(theme, faces), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
