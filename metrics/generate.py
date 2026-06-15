#!/usr/bin/env python3
# 床の間 — hand-made GitHub metrics SVG generator (sovereign, no third-party action).
#
# Reads the GitHub REST API with a fine-grained read-only PAT and renders a single
# static SVG in the "Encre & rose fané" signature palette. Aggregates private-repo
# volume WITHOUT ever emitting a private repository name (anti-leak invariant).
#
# Usage:
#   GITHUB_TOKEN=github_pat_xxx GITHUB_USER=LoloMutekai python3 metrics/generate.py
# Output: assets/metrics.svg
from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("metrics")

# --- API constants ----------------------------------------------------------
API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
USER_AGENT = "tokonoma-profile-metrics"
PER_PAGE = 100
MAX_REPOS = 300            # safety bound on pagination
MAX_COMMITS_PER_REPO = 100  # bound commit scan per repo for the hour heatmap
HTTP_TIMEOUT_SECS = 20

# --- composition constants --------------------------------------------------
TOP_LANGUAGES = 6          # languages shown in the bar
HEATMAP_HOURS = 24
HEATMAP_SPARK = "▁▂▃▄▅▆▇█"  # 8 levels

# --- palette "Encre & rose fané" (source of truth: PALETTE.md) --------------
INK = "#0d0e12"
SURFACE = "#16131a"
TEXT = "#8a93a6"
MUTED = "#5a6070"
TELL = "#c98ba0"        # the single rose accent — dose it
TELL_DIM = "#9c6f80"
LINE = "#2a2730"
CYAN = "#7fb8c8"         # cold neo-Tokyo counter-accent (sourd, matches header)

# --- neo-Tokyo scene constants ----------------------------------------------
GRID_LINES = 9          # perspective floor lines each side of the vanishing point
GRID_ROWS = 5           # horizontal floor rows (quadratic foreshortening)
SCANLINE_STEP = 4       # px between CRT scanlines

# --- SVG geometry -----------------------------------------------------------
SVG_W = 760
SVG_H = 488
PAD = 34
FONT_STACK = "'SFMono-Regular', 'JetBrains Mono', 'Cascadia Code', Consolas, monospace"


@dataclass(frozen=True)
class Metrics:
    """Aggregated, leak-safe GitHub stats. No private repo name ever appears here."""

    login: str
    created_year: int
    repo_count: int
    private_count: int
    language_bytes: dict[str, int] = field(default_factory=dict)
    commit_hours: tuple[int, ...] = ()  # 24 buckets, count per UTC hour
    commits_seen: int = 0

    @property
    def language_count(self) -> int:
        return len(self.language_bytes)

    @property
    def years_active(self) -> int:
        return max(1, datetime.now(timezone.utc).year - self.created_year + 1)


def _request(token: str, path: str) -> tuple[object, dict[str, str]]:
    """GET an API path. Returns (parsed_json, headers). Raises on hard failure."""
    url = path if path.startswith("http") else f"{API_ROOT}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", API_VERSION)
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECS) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        return payload, dict(resp.headers)


def _paginate(token: str, path: str, max_items: int) -> list[dict]:
    """Follow Link-header pagination up to max_items. Degrades to [] on error."""
    items: list[dict] = []
    sep = "&" if "?" in path else "?"
    next_url: str | None = f"{path}{sep}per_page={PER_PAGE}"
    while next_url and len(items) < max_items:
        try:
            payload, headers = _request(token, next_url)
        except urllib.error.HTTPError as exc:
            log.warning("pagination stopped at %s: HTTP %s", next_url, exc.code)
            break
        except (urllib.error.URLError, ValueError) as exc:
            log.warning("pagination stopped at %s: %s", next_url, exc)
            break
        if not isinstance(payload, list):
            break
        items.extend(payload)
        next_url = _parse_next_link(headers.get("Link", ""))
    return items[:max_items]


def _parse_next_link(link_header: str) -> str | None:
    """Extract the rel=next URL from a GitHub Link header, if any."""
    for part in link_header.split(","):
        segments = part.split(";")
        if len(segments) < 2:
            continue
        if 'rel="next"' in segments[1]:
            return segments[0].strip().strip("<>")
    return None


def fetch_metrics(token: str, user: str) -> Metrics:
    """Collect leak-safe aggregate metrics for the authenticated user."""
    profile, _ = _request(token, "/user")
    login = profile.get("login", user)
    created_year = _year_of(profile.get("created_at"))

    repos = _paginate(token, "/user/repos?affiliation=owner&visibility=all", MAX_REPOS)
    private_count = sum(1 for r in repos if r.get("private"))

    language_bytes: Counter[str] = Counter()
    hours = [0] * HEATMAP_HOURS
    commits_seen = 0

    for repo in repos:
        full_name = repo.get("full_name")
        if not full_name:
            continue
        language_bytes.update(_fetch_languages(token, full_name))
        repo_hours, n = _fetch_commit_hours(token, full_name, login)
        for h, c in enumerate(repo_hours):
            hours[h] += c
        commits_seen += n

    return Metrics(
        login=login,
        created_year=created_year,
        repo_count=len(repos),
        private_count=private_count,
        language_bytes=dict(language_bytes),
        commit_hours=tuple(hours),
        commits_seen=commits_seen,
    )


def _year_of(iso: str | None) -> int:
    if not iso:
        return datetime.now(timezone.utc).year
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).year
    except ValueError:
        log.warning("could not parse created_at=%r, defaulting to current year", iso)
        return datetime.now(timezone.utc).year


def _fetch_languages(token: str, full_name: str) -> dict[str, int]:
    """Bytes-per-language for a repo. Name is used only as a URL, never emitted."""
    try:
        payload, _ = _request(token, f"/repos/{full_name}/languages")
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        log.warning("languages unavailable for a repo: %s", exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def _fetch_commit_hours(token: str, full_name: str, author: str) -> tuple[list[int], int]:
    """Count this author's commits per UTC hour for a repo (bounded scan)."""
    hours = [0] * HEATMAP_HOURS
    commits = _paginate(
        token, f"/repos/{full_name}/commits?author={author}", MAX_COMMITS_PER_REPO
    )
    seen = 0
    for entry in commits:
        date = (entry.get("commit", {}) or {}).get("author", {}).get("date")
        if not date:
            continue
        try:
            hour = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(
                timezone.utc
            ).hour
        except ValueError:
            continue
        hours[hour] += 1
        seen += 1
    return hours, seen


# --- rendering (template injection — art is frozen, only data is injected) ---
import re

LANG_BAR_MAX = 55          # px: matches the background bar width in the template
LANG_SLOTS = 3             # languages shown in the constellation
TEMPLATE = Path(__file__).resolve().parent / "template.svg"


def _human(n: int) -> str:
    """1234 -> '1.2k', 980 -> '980'."""
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def _top_languages(language_bytes: dict[str, int], n: int) -> list[tuple[str, float]]:
    total = sum(language_bytes.values()) or 1
    ranked = sorted(language_bytes.items(), key=lambda kv: kv[1], reverse=True)
    return [(name, count / total) for name, count in ranked[:n]]


def _hour_sparkline(hours: tuple[int, ...]) -> str:
    """24-char sparkline of commit counts per UTC hour."""
    peak = max(hours) if hours else 0
    if peak == 0:
        return HEATMAP_SPARK[0] * HEATMAP_HOURS
    return "".join(
        HEATMAP_SPARK[round((c / peak) * (len(HEATMAP_SPARK) - 1))] for c in hours
    )


def _private_blocks(ratio: float) -> str:
    """A 7-cell gauge of filled/empty blocks for the private ratio (the rose tell)."""
    filled = round(ratio * 7)
    return "\u2593" * filled + "\u2591" * (7 - filled)


def _peak_hour(hours: tuple[int, ...]) -> int:
    return hours.index(max(hours)) if any(hours) else 0


def _short_lang(name: str) -> str:
    """Shorten a few long language names so they fit the narrow fragment column."""
    return {"TypeScript": "TS", "JavaScript": "JS"}.get(name, name)


def _inject(template: str, key: str, value: str) -> str:
    """Replace the text between <!--DATA:key--> and <!--/DATA:key--> markers."""
    pattern = re.compile(
        rf"(<!--DATA:{re.escape(key)}-->).*?(<!--/DATA:{re.escape(key)}-->)",
        re.DOTALL,
    )
    if not pattern.search(template):
        log.warning("template marker not found: %s", key)
        return template
    return pattern.sub(rf"\g<1>{escape(value)}\g<2>", template)


def _inject_bar(template: str, data_key: str, width_px: int) -> str:
    """Set the width of the filled language bar identified by its data-key."""
    pattern = re.compile(rf'(data-key="{re.escape(data_key)}" width=")\d+(")')
    if not pattern.search(template):
        log.warning("template bar not found: %s", data_key)
        return template
    return pattern.sub(rf"\g<1>{width_px}\g<2>", template)


def render_svg(m: Metrics) -> str:
    """Inject the real metrics into the frozen kakemono+constellation template.

    The art (kakemono, flow field, seal) is never drawn here — it lives in
    template.svg untouched. We only fill the <!--DATA:*--> slots, so an
    automated refresh can never break the composition.
    """
    svg = TEMPLATE.read_text(encoding="utf-8")

    ratio = m.private_count / m.repo_count if m.repo_count else 0.0
    langs = _top_languages(m.language_bytes, LANG_SLOTS)
    bar_keys = ("lang_python_w", "lang_ts_w", "lang_rust_w")  # template slot ids

    svg = _inject(svg, "repos", str(m.repo_count))
    svg = _inject(svg, "commits", _human(m.commits_seen))
    svg = _inject(svg, "private", _private_blocks(ratio))
    svg = _inject(svg, "since", str(m.created_year))
    svg = _inject(svg, "languages_count", str(m.language_count))
    svg = _inject(svg, "peak_hour", f"{_peak_hour(m.commit_hours):02d}h")
    svg = _inject(svg, "heatmap_spark", _hour_sparkline(m.commit_hours))

    for i in range(LANG_SLOTS):
        name, frac = langs[i] if i < len(langs) else ("\u2014", 0.0)
        svg = _inject(svg, f"lang{i + 1}_name", _short_lang(name))
        svg = _inject(svg, f"lang{i + 1}_pct", f"{frac * 100:.0f}%")
        svg = _inject_bar(svg, bar_keys[i], max(2, round(frac * LANG_BAR_MAX)))

    return svg


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    user = os.environ.get("GITHUB_USER", "LoloMutekai")
    if not token:
        log.error("no token: set GITHUB_TOKEN (or METRICS_TOKEN)")
        return 1

    try:
        metrics = fetch_metrics(token, user)
    except urllib.error.HTTPError as exc:
        log.error("API error %s: %s", exc.code, exc.reason)
        return 2
    except urllib.error.URLError as exc:
        log.error("network error: %s", exc)
        return 2

    svg = render_svg(metrics)
    # The world-image (kakemono + data constellation) IS the header.
    out = Path(__file__).resolve().parent.parent / "assets" / "tokonoma.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    log.info(
        "wrote %s — %d repos (%d private), %d langs, %d commits scanned",
        out,
        metrics.repo_count,
        metrics.private_count,
        metrics.language_count,
        metrics.commits_seen,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
