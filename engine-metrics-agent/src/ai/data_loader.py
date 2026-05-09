"""
V7P3R Engine Metrics - Data Loader
Loads and structures all v7p3r_bot game data, changelogs, and analysis
documents as context for the Gemini analysis agent.

IMPORTANT: This loader is EXCLUSIVELY for the v7p3r_bot lichess bot account.
It explicitly filters out: v7p3r human player games, C0BR4 bot, SlowMate bot.
"""

import os
import re
import io
import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import chess.pgn
    CHESS_AVAILABLE = True
except ImportError:
    CHESS_AVAILABLE = False

# ─── Workspace root resolution ───────────────────────────────────────────────

# engine-metrics-agent/src/ai/data_loader.py → engine-metrics/
_HERE = Path(__file__).resolve()
_AGENT_ROOT = _HERE.parent.parent.parent          # engine-metrics-agent/
_WORKSPACE_ROOT = _AGENT_ROOT.parent              # engine-metrics/

RAW_DATA_DIR        = _WORKSPACE_ROOT / "raw_data"
DATASETS_DIR        = _WORKSPACE_ROOT / "reporting_datasets"
V7P3R_DOCS_DIR      = RAW_DATA_DIR / "v7p3r_docs"
V7P3R_BOT_PGN_DIR   = RAW_DATA_DIR / "game_records" / "Lichess V7P3R Bot"
ANALYSIS_DIR        = RAW_DATA_DIR / "analysis_results"


# ─── CSV loading ─────────────────────────────────────────────────────────────

def load_game_data_csv(max_rows: int = 5000) -> list[dict]:
    """
    Load v7p3r_bot game metadata from the latest CSV.
    Returns a list of dicts with game-level metadata.
    """
    csv_path = DATASETS_DIR / "v7p3r_game_data_latest.csv"
    if not csv_path.exists():
        return []

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(row)
    return rows


def load_enhanced_summary_csv(max_rows: int = 2000) -> list[dict]:
    """
    Load enhanced game summary data.
    """
    csv_path = DATASETS_DIR / "v7p3r_game_summary_enhanced_latest.csv"
    if not csv_path.exists():
        return []

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(row)
    return rows


# ─── Changelog loading ───────────────────────────────────────────────────────

def load_changelog(max_chars: int = 40000) -> str:
    """
    Load the v7p3r engine CHANGELOG.md - the source of truth for
    version history, changes, and development timeline.
    """
    changelog_path = V7P3R_DOCS_DIR / "CHANGELOG.md"
    if not changelog_path.exists():
        return ""

    text = changelog_path.read_text(encoding="utf-8", errors="ignore")
    if len(text) > max_chars:
        # Keep the most recent section (beginning of file) for context
        text = text[:max_chars] + "\n\n[... changelog truncated for context window ...]"
    return text


# ─── Doc loading from raw_data/v7p3r_docs ────────────────────────────────────

def load_v7p3r_docs(max_docs: int = 10, max_chars_each: int = 8000) -> list[dict]:
    """
    Load key design/build documents from raw_data/v7p3r_docs.
    Prioritizes recent docs (by filename date/version).
    """
    if not V7P3R_DOCS_DIR.exists():
        return []

    docs = []
    # Sort by name (picks up version numbers naturally: v10, v11, v12...)
    md_files = sorted(V7P3R_DOCS_DIR.glob("*.md"), key=lambda p: p.name, reverse=True)

    # Always include CHANGELOG.md first (separately loaded) - skip here
    for path in md_files:
        if path.name == "CHANGELOG.md":
            continue
        if len(docs) >= max_docs:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if len(text) > max_chars_each:
                text = text[:max_chars_each] + "\n\n[... document truncated ...]"
            docs.append({"filename": path.name, "content": text})
        except Exception:
            pass

    return docs


def parse_current_version_from_changelog(changelog_text: str) -> Optional[str]:
    """
    Parse the most recently DEPLOYED/ACTIVE version from the CHANGELOG.

    Strategy: split the changelog into per-section blocks (by markdown headers)
    and evaluate each block independently so Version and Status are never
    matched across section boundaries.

    Acceptance rules (must ALL be true):
      - Block contains **Version**: vX.Y
      - Block contains **Status**: <value>
      - Status does NOT contain RETIRED, ROLLED BACK, or ROLLBACK

    Rejection is explicit — a version with no status, or a status that
    contains RETIRED/ROLLED BACK, is skipped entirely. There is no fallback
    to the first version found, because that could return a RETIRED version.

    Returns None if no currently-deployed version can be determined.
    """
    if not changelog_text:
        return None

    _VER_RE    = re.compile(r'\*\*Version\*\*:\s*(v[\d]+(?:[\.\d]+)*(?:[\w.-]*)?)', re.IGNORECASE)
    _STATUS_RE = re.compile(r'\*\*Status\*\*:\s*([^\n]+)', re.IGNORECASE)

    _REJECTED_STATUSES = ('RETIRED', 'ROLLED BACK', 'ROLLBACK')
    _ACCEPTED_STATUSES = ('DEPLOYED', 'ACTIVE')

    # Split on any markdown header line (##, ###, ####, etc.)
    blocks = re.split(r'\n(?=#{2,6}\s)', changelog_text)

    for block in blocks:
        ver_match = _VER_RE.search(block)
        if not ver_match:
            continue

        status_match = _STATUS_RE.search(block)
        if not status_match:
            continue

        status_raw = status_match.group(1).strip().upper()

        # Explicit rejection — never return a RETIRED/ROLLED BACK version
        if any(bad in status_raw for bad in _REJECTED_STATUSES):
            continue

        # Accept only confirmed DEPLOYED or ACTIVE versions
        if any(good in status_raw for good in _ACCEPTED_STATUSES):
            return ver_match.group(1).strip()

    return None  # No currently-deployed version found in changelog


def load_notation_events() -> list[dict]:
    """
    Load the operational events notation dataset from raw_data/notation_events.json.

    This file records significant non-engine-code events that affect metrics:
    config changes, matchmaking on/off, infrastructure changes, operational
    decisions, lichess-bot tuning, etc.

    Returns a list of event dicts, sorted newest-first by date.
    """
    path = RAW_DATA_DIR / "notation_events.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events", [])
        # Sort newest-first (ISO date strings sort correctly as strings)
        events.sort(key=lambda e: e.get("date", ""), reverse=True)
        return events
    except Exception:
        return []


def load_extra_raw_data(max_docs: int = 5) -> list[dict]:
    """
    Load any additional markdown or JSON files the user has placed
    in raw_data/ (top level) for the agent to consider.
    Skips notation_events.json (loaded separately via load_notation_events).
    """
    docs = []
    for ext in ("*.md", "*.txt", "*.json"):
        for path in RAW_DATA_DIR.glob(ext):
            if path.name == "notation_events.json":
                continue  # loaded separately
            if len(docs) >= max_docs:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:6000]
                docs.append({"filename": path.name, "content": text})
            except Exception:
                pass
    return docs


def load_latest_stockfish_analysis() -> Optional[dict]:
    """
    Load the most recent Stockfish error analysis results from
    raw_data/analysis_results/ (generated by scripts/analyze_ytd_games.py).
    
    Returns the JSON data dict containing blunders, mistakes, and pattern analysis.
    Returns None if no analysis files are found.
    """
    if not ANALYSIS_DIR.exists():
        return None
    
    # Find the most recent JSON analysis file (v18_3_ytd_analysis_*.json)
    json_files = sorted(
        ANALYSIS_DIR.glob("v18_3_ytd_analysis_*.json"),
        key=lambda p: p.name,
        reverse=True  # Most recent first
    )
    
    if not json_files:
        return None
    
    latest_file = json_files[0]
    try:
        data = json.loads(latest_file.read_text(encoding="utf-8"))
        # Attach metadata for reference
        data["_analysis_file"] = latest_file.name
        data["_analysis_timestamp"] = latest_file.stat().st_mtime
        return data
    except Exception:
        return None


# ─── PGN loading ─────────────────────────────────────────────────────────────

def load_recent_pgn_games(max_games: int = 200) -> list[dict]:
    """
    Load the most recent v7p3r_bot PGN file and parse up to max_games.
    Returns a list of game header dicts with optional move text.
    """
    if not V7P3R_BOT_PGN_DIR.exists() or not CHESS_AVAILABLE:
        return []

    # Find the most recent PGN (by filename date)
    pgn_files = sorted(
        [p for p in V7P3R_BOT_PGN_DIR.glob("*.pgn")
         if "annotated" not in p.name.lower()],
        key=lambda p: p.name,
        reverse=True
    )
    if not pgn_files:
        return []

    pgn_path = pgn_files[0]
    games = []

    with open(pgn_path, encoding="utf-8", errors="ignore") as f:
        while len(games) < max_games:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            headers = dict(game.headers)
            # Quick sanity: only v7p3r_bot player side
            white = headers.get("White", "").lower()
            black = headers.get("Black", "").lower()
            if "v7p3r_bot" not in white and "v7p3r_bot" not in black:
                continue

            games.append({
                "source_pgn": pgn_path.name,
                "event": headers.get("Event", ""),
                "date": headers.get("Date", ""),
                "white": headers.get("White", ""),
                "black": headers.get("Black", ""),
                "result": headers.get("Result", ""),
                "eco": headers.get("ECO", ""),
                "opening": headers.get("Opening", ""),
                "time_control": headers.get("TimeControl", ""),
                "termination": headers.get("Termination", ""),
                "white_elo": headers.get("WhiteElo", ""),
                "black_elo": headers.get("BlackElo", ""),
            })

    return games


def load_pgn_text(pgn_path: str) -> str:
    """
    Load raw PGN text from a given path.
    Used by stockfish_tools for move-by-move analysis.
    """
    path = Path(pgn_path)
    if not path.exists():
        raise FileNotFoundError(f"PGN not found: {pgn_path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def get_latest_pgn_path() -> Optional[Path]:
    """Return the path to the most recent v7p3r_bot PGN file."""
    if not V7P3R_BOT_PGN_DIR.exists():
        return None
    files = sorted(
        [p for p in V7P3R_BOT_PGN_DIR.glob("*.pgn")
         if "annotated" not in p.name.lower()],
        key=lambda p: p.name,
        reverse=True
    )
    return files[0] if files else None


# ─── Statistics summary ───────────────────────────────────────────────────────

def build_stats_summary(games: list[dict]) -> dict:
    """
    Compute quick aggregate stats from a list of game data dicts
    (as returned by load_game_data_csv).
    """
    if not games:
        return {}

    total = len(games)
    outcomes = {"win": 0, "loss": 0, "draw": 0}
    by_version: dict[str, dict] = {}
    by_color: dict[str, dict] = {}
    elo_values = []

    for g in games:
        outcome = g.get("outcome", "").lower()
        if outcome in outcomes:
            outcomes[outcome] += 1

        ver = g.get("engine_version", "unknown")
        if ver not in by_version:
            by_version[ver] = {"win": 0, "loss": 0, "draw": 0, "total": 0}
        by_version[ver]["total"] += 1
        if outcome in by_version[ver]:
            by_version[ver][outcome] += 1

        color = g.get("color", "").lower()
        if color not in by_color:
            by_color[color] = {"win": 0, "loss": 0, "draw": 0, "total": 0}
        by_color[color]["total"] += 1
        if outcome in by_color[color]:
            by_color[color][outcome] += 1

        try:
            elo_values.append(int(g.get("v7p3r_elo", 0)))
        except (ValueError, TypeError):
            pass

    win_rate = round(outcomes["win"] / total * 100, 1) if total > 0 else 0
    avg_elo = round(sum(elo_values) / len(elo_values)) if elo_values else 0
    latest_elo = elo_values[-1] if elo_values else 0

    return {
        "total_games": total,
        "win_rate_pct": win_rate,
        "wins": outcomes["win"],
        "losses": outcomes["loss"],
        "draws": outcomes["draw"],
        "avg_elo": avg_elo,
        "latest_elo": latest_elo,
        "by_engine_version": by_version,
        "by_color": by_color,
    }


# ─── Context package for the agent ───────────────────────────────────────────

def build_agent_context(
    include_pgn_games: bool = True,
    include_docs: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Build the full context package that will be injected into the
    Gemini agent's system prompt and first-turn context.

    Returns a dict with clearly labeled sections.
    """
    if verbose:
        print("[DataLoader] Loading v7p3r_bot game data...")

    game_data = load_game_data_csv(max_rows=5000)
    stats = build_stats_summary(game_data)
    changelog = load_changelog()
    docs = load_v7p3r_docs(max_docs=8) if include_docs else []
    extra = load_extra_raw_data(max_docs=5)
    notation_events = load_notation_events()
    pgn_games = load_recent_pgn_games(max_games=150) if include_pgn_games else []
    stockfish_analysis = load_latest_stockfish_analysis()

    if verbose:
        n_games = len(game_data)
        n_pgn = len(pgn_games)
        n_docs = len(docs) + len(extra)
        analysis_status = "✓" if stockfish_analysis else "✗"
        print(f"[DataLoader] Loaded {n_games} game records, {n_pgn} recent PGN games, "
              f"{n_docs} docs, {len(notation_events)} notation events, "
              f"Stockfish analysis: {analysis_status}")

    # Serialize latest PGN game headers as a compact table
    pgn_summary = _pgn_games_to_table(pgn_games[:50]) if pgn_games else ""

    # Latest version: CHANGELOG is the authoritative source; CSV game data may lag.
    # csv_version is ONLY used to describe the dataset range — never as a proxy
    # for the deployed version, since CSV data can contain RETIRED versions.
    changelog_version = parse_current_version_from_changelog(changelog)
    csv_version = "unknown"
    if game_data:
        for g in reversed(game_data):
            ver = g.get("engine_version", "")
            if ver:
                csv_version = ver
                break
    # If the changelog has no clear DEPLOYED/ACTIVE version, surface that gap
    # honestly rather than guessing from the CSV.
    latest_version = changelog_version if changelog_version else "unknown (check CHANGELOG)"

    if verbose and changelog_version and changelog_version != csv_version:
        print(f"[DataLoader] Note: CHANGELOG version ({changelog_version}) differs "
              f"from CSV version ({csv_version}) — using CHANGELOG as authoritative")

    ctx = {
        "stats": stats,
        "latest_version": latest_version,
        "csv_version": csv_version,              # version reported by game CSV (may lag)
        "changelog_version": changelog_version,  # version per CHANGELOG (authoritative)
        "notation_events": notation_events,       # operational events log (non-engine changes)
        "changelog_excerpt": changelog[:12000],  # first 12k chars
        "pgn_recent_games_table": pgn_summary,
        "pgn_game_count": len(pgn_games),
        "design_docs": docs,
        "extra_raw_data": extra,
        "stockfish_analysis": stockfish_analysis,  # Latest error analysis results
        "data_paths": {
            "game_csv": str(DATASETS_DIR / "v7p3r_game_data_latest.csv"),
            "pgn_dir": str(V7P3R_BOT_PGN_DIR),
            "docs_dir": str(V7P3R_DOCS_DIR),
            "raw_data_dir": str(RAW_DATA_DIR),
            "notation_events": str(RAW_DATA_DIR / "notation_events.json"),
            "analysis_results_dir": str(ANALYSIS_DIR),
        },
    }
    return ctx


def _pgn_games_to_table(games: list[dict]) -> str:
    """Format PGN game list as a compact markdown table."""
    if not games:
        return ""
    header = "| Date | White | Black | Result | Opening | TC | Termination |\n"
    sep    = "|------|-------|-------|--------|---------|----|--------------|\n"
    rows = []
    for g in games:
        rows.append(
            f"| {g.get('date','')} | {g.get('white','')} | {g.get('black','')} "
            f"| {g.get('result','')} | {g.get('opening','')[:30]} "
            f"| {g.get('time_control','')} | {g.get('termination','')} |"
        )
    return header + sep + "\n".join(rows)


def context_to_prompt_text(ctx: dict) -> str:
    """
    Convert the context dict into a formatted text block suitable for
    injection into a system prompt or first user message.
    """
    stats = ctx.get("stats", {})
    lines = [
        "=" * 63,
        "  V7P3R BOT - ENGINE METRICS KNOWLEDGE BASE",
        "=" * 63,
        "",
        f"Current deployed version (from CHANGELOG): {ctx.get('latest_version', 'unknown')}",
        f"Latest version in game CSV dataset: {ctx.get('csv_version', 'unknown')}",
        f"NOTE: The game CSV dataset may not include games from the most recent engine "
        f"versions. Always trust the CHANGELOG for the current deployed version.",
        f"Total games in CSV dataset: {stats.get('total_games', 0)}",
        f"Overall win rate: {stats.get('win_rate_pct', 0)}%  "
        f"(W:{stats.get('wins',0)} / L:{stats.get('losses',0)} / D:{stats.get('draws',0)})",
        f"Average ELO: {stats.get('avg_elo', 0)}   Latest ELO: {stats.get('latest_elo', 0)}",
        "",
    ]

    # Per-version performance
    by_ver = stats.get("by_engine_version", {})
    if by_ver:
        lines.append("--- Performance by engine version ---")
        for ver, s in sorted(by_ver.items(), key=lambda x: x[0]):
            t = s.get("total", 1) or 1
            wr = round(s.get("win", 0) / t * 100, 1)
            lines.append(f"  {ver:12s}  games={s.get('total',0):5d}  win%={wr}")
        lines.append("")

    # Changelog excerpt
    if ctx.get("changelog_excerpt"):
        lines.append("--- CHANGELOG (engine version deployments) ---")
        lines.append(ctx["changelog_excerpt"])
        lines.append("")

    # Notation events — operational changes that explain metric shifts
    notation_events = ctx.get("notation_events", [])
    if notation_events:
        lines.append("--- OPERATIONAL EVENTS (non-engine changes affecting metrics) ---")
        lines.append("IMPORTANT: When analyzing metric shifts, always check whether a")
        lines.append("notation event (config/matchmaking/tuning change) coincides with")
        lines.append("the date range before attributing the change to the chess engine.")
        lines.append("")
        for ev in notation_events:
            approx = "~" if ev.get("date_approximate") else ""
            lines.append(f"  [{approx}{ev.get('date','')}] [{ev.get('type','').upper()}] {ev.get('title','')}")
            lines.append(f"    Scope: {ev.get('change_scope','unknown')}  |  Engine: {ev.get('engine_version_affected','?')}")
            lines.append(f"    {ev.get('description','')}")
            if ev.get("expected_metric_impact"):
                lines.append(f"    Impact: {ev.get('expected_metric_impact')}")
            lines.append("")
        lines.append("")

    # Design docs (titles only in system prompt, content available on request)
    docs = ctx.get("design_docs", [])
    if docs:
        lines.append("--- Available design/build documents ---")
        for d in docs:
            lines.append(f"  - {d['filename']}")
        lines.append("")

    # Stockfish error analysis results
    analysis = ctx.get("stockfish_analysis")
    if analysis:
        lines.append("=" * 63)
        lines.append("  STOCKFISH ERROR ANALYSIS - 2026 YTD GAMES")
        lines.append("=" * 63)
        
        metadata = analysis.get('metadata', {})
        patterns = analysis.get('patterns', {})
        summary = patterns.get('summary', {})
        v7p3r_stats = patterns.get('v7p3r_stats', {})
        opening_patterns = patterns.get('opening_patterns', {})
        move_patterns = patterns.get('move_number_patterns', {})
        
        lines.append(f"Analysis file: {analysis.get('_analysis_file', 'unknown')}")
        lines.append(f"Analysis date: {metadata.get('analysis_date', 'unknown')}")
        lines.append(f"Analysis depth: {metadata.get('stockfish_depth', '?')}")
        lines.append(f"Games analyzed: {metadata.get('total_games', 0)}")
        lines.append(f"Engine version: {metadata.get('version', 'unknown')}")
        lines.append(f"Time period: {metadata.get('year', 'unknown')}")
        lines.append("")
        
        if v7p3r_stats or summary:
            lines.append("OVERALL ERROR STATISTICS:")
            lines.append(f"  Total errors: {v7p3r_stats.get('total_errors', 0)}")
            lines.append(f"  Blunders per game: {v7p3r_stats.get('blunders_per_game', 0):.2f}")
            lines.append(f"  Mistakes per game: {v7p3r_stats.get('mistakes_per_game', 0):.2f}")
            lines.append(f"  Average accuracy: {summary.get('v7p3r_avg_accuracy', 0):.1f}%")
            lines.append(f"  Games as White: {summary.get('v7p3r_as_white', 0)}")
            lines.append(f"  Games as Black: {summary.get('v7p3r_as_black', 0)}")
            lines.append("")
            
            # Opening problems
            if opening_patterns:
                lines.append("PROBLEMATIC OPENINGS (Top 5 by error count):")
                # Calculate total errors and sort descending
                opening_with_totals = []
                for opening, data in opening_patterns.items():
                    total = data.get('blunders', 0) + data.get('mistakes', 0)
                    games = data.get('games', 0)
                    opening_with_totals.append((opening, total, games))
                
                sorted_openings = sorted(opening_with_totals, key=lambda x: x[1], reverse=True)[:5]
                for opening, errors, games in sorted_openings:
                    avg = errors / games if games > 0 else 0
                    lines.append(f"  {opening[:50]}: {errors} errors ({games} games, {avg:.1f} errors/game)")
                lines.append("")
            
            # Move phase weaknesses
            if move_patterns:
                lines.append("ERRORS BY MOVE NUMBER (Top 5 worst phases):")
                # Calculate total errors and sort
                move_with_totals = []
                for move_num, data in move_patterns.items():
                    if isinstance(data, dict):
                        total = data.get('blunders', 0) + data.get('mistakes', 0)
                        move_with_totals.append((move_num, total, data))
                    else:
                        move_with_totals.append((move_num, data, None))
                
                sorted_phases = sorted(move_with_totals, key=lambda x: x[1], reverse=True)[:5]
                for move_range, total_errors, details in sorted_phases:
                    if details:
                        blunders = details.get('blunders', 0)
                        mistakes = details.get('mistakes', 0)
                        lines.append(f"  Move {move_range}: {total_errors} errors ({blunders} blunders, {mistakes} mistakes)")
                    else:
                        lines.append(f"  Move {move_range}: {total_errors} errors")
                lines.append("")
        
        lines.append("INSIGHTS:")
        lines.append("- Use this analysis to identify tactical weaknesses and opening problems")
        lines.append("- Compare error rates across different game phases and openings")
        lines.append("- Look for patterns in when/where the engine makes mistakes")
        lines.append("")

    # Recent PGN game summary
    if ctx.get("pgn_recent_games_table"):
        lines.append(f"--- Recent {ctx.get('pgn_game_count',0)} PGN games (latest {len(ctx['pgn_recent_games_table'].splitlines())-2} shown) ---")
        lines.append(ctx["pgn_recent_games_table"])
        lines.append("")

    lines.append("=" * 63)
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick smoke test
    ctx = build_agent_context(verbose=True)
    output = context_to_prompt_text(ctx)
    sys.stdout.buffer.write(output.encode("utf-8", errors="replace") + b"\n")
