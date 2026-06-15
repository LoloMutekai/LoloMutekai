#!/usr/bin/env bash
# Render an SVG to PNG via headless chromium, PLAYING CSS animations.
#
# Why not rsvg-convert: rsvg does NOT execute @keyframes, so it freezes the
# initial state (invisible stroke-dashoffset curves, un-pulsed glow) and lies
# about the result. Chromium runs the animations, then we screenshot a frame.
#
# The SVG is inlined into an HTML wrapper (NOT referenced via <img src>, which
# would screenshot before the file loads).
#
# Usage: render_chromium.sh <input.svg> <output.png> [virtual_time_budget_ms]
#   budget ~5500  -> mid-animation frame (drawing in progress)
#   budget 11000+ -> final state (what the profile page shows after Camo raster)
set -euo pipefail

SVG="${1:?usage: render_chromium.sh <svg> <png> [budget_ms]}"
OUT="${2:?usage: render_chromium.sh <svg> <png> [budget_ms]}"
BUDGET="${3:-11000}"

readonly CANVAS_W=1000
readonly CANVAS_H=640        # match the SVG viewBox height
readonly BG="#0d1117"        # GitHub dark background

html="$(mktemp /tmp/_svgwrap.XXXXXX.html)"
trap 'rm -f "$html"' EXIT

{
  printf '<!doctype html><meta charset=utf-8>'
  printf '<style>html,body{margin:0;background:%s}svg{display:block;width:%dpx;height:%dpx}</style>' \
    "$BG" "$CANVAS_W" "$CANVAS_H"
  cat "$SVG"
} > "$html"

chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size="${CANVAS_W},${CANVAS_H}" \
  --virtual-time-budget="$BUDGET" --screenshot="$OUT" "file://$html" 2>/dev/null

echo "rendered: $OUT (budget ${BUDGET}ms)"
