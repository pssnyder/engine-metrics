#!/usr/bin/env python3
"""
Batch Analysis Script - All 2026 v18.3 Games
Analyzes all YTD games with Stockfish to identify patterns in blunders, mistakes, and missed opportunities.
Generates a comprehensive improvement report.

Usage:
    python scripts/analyze_ytd_games.py                    # analyze all 2026 games
    python scripts/analyze_ytd_games.py --depth 20         # deeper analysis (slower)
    python scripts/analyze_ytd_games.py --quick            # depth 15 for speed
    python scripts/analyze_ytd_games.py --max-games 20     # limit to first N games
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Any

# Add the AI module to path
_ROOT = Path(__file__).resolve().parent.parent
_AI_DIR = _ROOT / "engine-metrics-agent" / "src" / "ai"
sys.path.insert(0, str(_AI_DIR))

try:
    import chess
    import chess.pgn
    from stockfish_tools import analyze_game_pgn
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    from rich import print as rprint
    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"Error: Missing dependencies. {e}", file=sys.stderr)
    print("Run: pip install python-chess rich", file=sys.stderr)
    DEPS_AVAILABLE = False
    sys.exit(1)

console = Console()


# ─── Configuration ────────────────────────────────────────────────────────────

PGN_DIR = _ROOT / "raw_data" / "game_records" / "Lichess V7P3R Bot"
OUTPUT_DIR = _ROOT / "raw_data" / "analysis_results"


# ─── Load PGN Games ───────────────────────────────────────────────────────────

def load_games_from_pgn(pgn_path: Path, max_games: int = None, year_filter: int = 2026) -> List[str]:
    """Load individual games from a PGN file as text strings, filtered by year."""
    games = []
    skipped = 0
    
    with open(pgn_path, encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            
            # Filter by year from Date header
            date_str = game.headers.get("Date", "")
            if date_str:
                try:
                    game_year = int(date_str.split(".")[0])
                    if game_year != year_filter:
                        skipped += 1
                        continue
                except (ValueError, IndexError):
                    pass  # Include games with unparseable dates
            
            # Convert game back to PGN text
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            pgn_text = game.accept(exporter)
            games.append(pgn_text)
            
            if max_games and len(games) >= max_games:
                break
    
    if skipped > 0:
        console.print(f"  [dim]Skipped {skipped} games from other years in {pgn_path.name}[/dim]")
    
    return games


def load_all_2026_games(max_games: int = None) -> List[Dict[str, Any]]:
    """Load games from the latest cumulative 2026 PGN file, filtered to only 2026 games."""
    if not PGN_DIR.exists():
        console.print(f"[red]Error:[/red] PGN directory not found: {PGN_DIR}")
        sys.exit(1)
    
    # Use the latest cumulative export file (files are cumulative, so we only need the newest)
    target_file = PGN_DIR / "lichess_v7p3r_bot_2026-04-09.pgn"
    
    if not target_file.exists():
        console.print(f"[red]Error:[/red] Target PGN file not found: {target_file}")
        console.print(f"[yellow]Available files:[/yellow]")
        for f in sorted(PGN_DIR.glob("lichess_v7p3r_bot_2026-*.pgn")):
            console.print(f"  - {f.name}")
        sys.exit(1)
    
    console.print(f"[cyan]Loading from:[/cyan] {target_file.name}")
    
    games_text = load_games_from_pgn(
        target_file, 
        max_games=max_games,
        year_filter=2026
    )
    
    console.print(f"[green]✓[/green] Loaded {len(games_text)} games from 2026")
    
    all_games = [
        {
            "source_file": target_file.name,
            "pgn_text": pgn_text
        }
        for pgn_text in games_text
    ]
    
    return all_games


# ─── Analyze Games ────────────────────────────────────────────────────────────

def analyze_games_batch(games: List[Dict], depth: int = 18) -> List[Dict]:
    """Run Stockfish analysis on all games."""
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Analyzing {len(games)} games (depth={depth})...", total=len(games))
        
        for i, game in enumerate(games, 1):
            try:
                analysis = analyze_game_pgn(
                    pgn_text=game["pgn_text"],
                    depth=depth,
                    blunder_threshold_cp=150,
                    mistake_threshold_cp=80,
                    max_moves=120
                )
                
                if "error" not in analysis:
                    results.append({
                        "game_index": i,
                        "source_file": game["source_file"],
                        "analysis": analysis
                    })
                else:
                    console.print(f"[yellow]Skipped game {i}:[/yellow] {analysis['error']}")
                
            except Exception as e:
                console.print(f"[red]Error analyzing game {i}:[/red] {e}")
            
            progress.update(task, advance=1)
    
    return results


# ─── Aggregate Patterns ───────────────────────────────────────────────────────

def aggregate_patterns(results: List[Dict]) -> Dict[str, Any]:
    """Extract patterns and insights from analysis results."""
    
    # Initialize counters
    total_games = len(results)
    v7p3r_as_white = 0
    v7p3r_as_black = 0
    
    blunders_white = []
    blunders_black = []
    mistakes_white = []
    mistakes_black = []
    inaccuracies_white = []
    inaccuracies_black = []
    
    # v7p3r-specific error tracking (only v7p3r's errors, not opponent's)
    v7p3r_blunders = []
    v7p3r_mistakes = []
    v7p3r_inaccuracies = []
    v7p3r_accuracy_scores = []
    
    opening_patterns = defaultdict(lambda: {"blunders": 0, "mistakes": 0, "games": 0})
    move_number_errors = defaultdict(lambda: {"blunders": 0, "mistakes": 0, "count": 0})
    
    for game_result in results:
        analysis = game_result["analysis"]
        headers = analysis.get("game_headers", {})
        
        # Determine v7p3r color
        white_name = headers.get("White", "").lower()
        black_name = headers.get("Black", "").lower()
        v7p3r_color = "white" if "v7p3r" in white_name else "black" if "v7p3r" in black_name else None
        
        if v7p3r_color == "white":
            v7p3r_as_white += 1
            v7p3r_accuracy_scores.append(analysis.get("white_accuracy_pct", 0))
        elif v7p3r_color == "black":
            v7p3r_as_black += 1
            v7p3r_accuracy_scores.append(analysis.get("black_accuracy_pct", 0))
        
        # Collect ALL errors by color (for overall stats)
        for blunder in analysis.get("blunders", []):
            if blunder["mover"] == "white":
                blunders_white.append(blunder)
            else:
                blunders_black.append(blunder)
            
            # Track only v7p3r's errors for pattern analysis
            if blunder["mover"] == v7p3r_color:
                v7p3r_blunders.append(blunder)
                
                # Track move number patterns (v7p3r only)
                move_num = (blunder["ply"] + 1) // 2
                move_bucket = (move_num // 5) * 5  # Group by 5-move buckets (0-4, 5-9, etc.)
                move_number_errors[move_bucket]["blunders"] += 1
                move_number_errors[move_bucket]["count"] += 1
        
        for mistake in analysis.get("mistakes", []):
            if mistake["mover"] == "white":
                mistakes_white.append(mistake)
            else:
                mistakes_black.append(mistake)
            
            # Track only v7p3r's errors
            if mistake["mover"] == v7p3r_color:
                v7p3r_mistakes.append(mistake)
                
                move_num = (mistake["ply"] + 1) // 2
                move_bucket = (move_num // 5) * 5
                move_number_errors[move_bucket]["mistakes"] += 1
                move_number_errors[move_bucket]["count"] += 1
        
        for inacc in analysis.get("inaccuracies", []):
            if inacc["mover"] == "white":
                inaccuracies_white.append(inacc)
            else:
                inaccuracies_black.append(inacc)
            
            if inacc["mover"] == v7p3r_color:
                v7p3r_inaccuracies.append(inacc)
        
        # Opening patterns (v7p3r errors only)
        opening = headers.get("Opening", "Unknown")
        opening_patterns[opening]["games"] += 1
        opening_patterns[opening]["blunders"] += len([b for b in analysis.get("blunders", []) if b["mover"] == v7p3r_color])
        opening_patterns[opening]["mistakes"] += len([m for m in analysis.get("mistakes", []) if m["mover"] == v7p3r_color])
    
    # Calculate v7p3r-specific aggregates
    avg_accuracy = sum(v7p3r_accuracy_scores) / len(v7p3r_accuracy_scores) if v7p3r_accuracy_scores else 0
    
    return {
        "summary": {
            "total_games_analyzed": total_games,
            "v7p3r_as_white": v7p3r_as_white,
            "v7p3r_as_black": v7p3r_as_black,
            "total_blunders_white": len(blunders_white),
            "total_blunders_black": len(blunders_black),
            "total_mistakes_white": len(mistakes_white),
            "total_mistakes_black": len(mistakes_black),
            "v7p3r_avg_accuracy": round(avg_accuracy, 2),
        },
        "v7p3r_stats": {
            "blunders_per_game": round(len(v7p3r_blunders) / total_games, 2) if total_games > 0 else 0,
            "mistakes_per_game": round(len(v7p3r_mistakes) / total_games, 2) if total_games > 0 else 0,
            "total_errors": len(v7p3r_blunders) + len(v7p3r_mistakes),
        },
        "opening_patterns": dict(opening_patterns),
        "move_number_patterns": dict(move_number_errors),
        "raw_data": {
            "blunders_white": blunders_white,
            "blunders_black": blunders_black,
            "mistakes_white": mistakes_white,
            "mistakes_black": mistakes_black,
        }
    }


# ─── Generate Report ──────────────────────────────────────────────────────────

def print_summary_report(patterns: Dict[str, Any]):
    """Print a formatted summary to console."""
    console.print("\n[bold cyan]═══ 2026 YTD Game Analysis Report ═══[/bold cyan]\n")
    
    summary = patterns["summary"]
    v7p3r = patterns["v7p3r_stats"]
    
    # Summary stats
    table = Table(title="Overall Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Games Analyzed", str(summary["total_games_analyzed"]))
    table.add_row("v7p3r as White", str(summary["v7p3r_as_white"]))
    table.add_row("v7p3r as Black", str(summary["v7p3r_as_black"]))
    table.add_row("", "")
    table.add_row("v7p3r Blunders/Game", f"{v7p3r['blunders_per_game']:.2f}")
    table.add_row("v7p3r Mistakes/Game", f"{v7p3r['mistakes_per_game']:.2f}")
    table.add_row("v7p3r Total Errors", str(v7p3r['total_errors']))
    table.add_row("", "")
    table.add_row("v7p3r Avg Accuracy", f"{summary['v7p3r_avg_accuracy']:.1f}%")
    
    console.print(table)
    
    # Opening patterns
    console.print("\n[bold cyan]Problematic Openings (Top 5)[/bold cyan]")
    openings = patterns["opening_patterns"]
    sorted_openings = sorted(
        openings.items(),
        key=lambda x: x[1]["blunders"] + x[1]["mistakes"],
        reverse=True
    )[:5]
    
    opening_table = Table(show_header=True)
    opening_table.add_column("Opening", style="cyan")
    opening_table.add_column("Games", justify="right")
    opening_table.add_column("Blunders", justify="right", style="red")
    opening_table.add_column("Mistakes", justify="right", style="yellow")
    
    for opening, stats in sorted_openings:
        opening_table.add_row(
            opening[:50],  # Truncate long names
            str(stats["games"]),
            str(stats["blunders"]),
            str(stats["mistakes"])
        )
    
    console.print(opening_table)
    
    # Move number patterns
    console.print("\n[bold cyan]Errors by Game Phase[/bold cyan]")
    move_table = Table(show_header=True)
    move_table.add_column("Moves", style="cyan")
    move_table.add_column("Blunders", justify="right", style="red")
    move_table.add_column("Mistakes", justify="right", style="yellow")
    move_table.add_column("Total", justify="right", style="white")
    
    move_patterns = sorted(patterns["move_number_patterns"].items())
    for move_range, stats in move_patterns[:8]:  # First 40 moves
        move_table.add_row(
            f"{move_range}-{move_range+4}",
            str(stats["blunders"]),
            str(stats["mistakes"]),
            str(stats["blunders"] + stats["mistakes"])
        )
    
    console.print(move_table)
    
    console.print("\n[green]✓[/green] Full analysis saved to JSON file\n")


def save_results(results: List[Dict], patterns: Dict[str, Any], depth: int):
    """Save analysis results to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"v18_3_ytd_analysis_{timestamp}.json"
    output_path = OUTPUT_DIR / filename
    
    output_data = {
        "metadata": {
            "analysis_date": datetime.now().isoformat(),
            "total_games": len(results),
            "stockfish_depth": depth,
            "version": "v18.3",
            "year": 2026,
        },
        "patterns": patterns,
        "game_results": results,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    
    console.print(f"[green]✓[/green] Results saved to: [cyan]{output_path}[/cyan]")
    
    # Also create a markdown report
    md_filename = f"v18_3_ytd_analysis_{timestamp}.md"
    md_path = OUTPUT_DIR / md_filename
    
    generate_markdown_report(md_path, patterns, depth)


def generate_markdown_report(path: Path, patterns: Dict[str, Any], depth: int):
    """Generate a human-readable markdown report."""
    summary = patterns["summary"]
    v7p3r = patterns["v7p3r_stats"]
    
    content = f"""# v7p3r_bot 2026 YTD Analysis Report

**Analysis Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  
**Stockfish Depth:** {depth}  
**Games Analyzed:** {summary['total_games_analyzed']}  
**Engine Version:** v18.3

---

## Executive Summary

- **Total Errors (v7p3r):** {v7p3r['total_errors']} blunders + mistakes across {summary['total_games_analyzed']} games
- **Blunders per Game:** {v7p3r['blunders_per_game']:.2f}
- **Mistakes per Game:** {v7p3r['mistakes_per_game']:.2f}
- **Average Accuracy:** {summary['v7p3r_avg_accuracy']:.1f}%

### Color Distribution
- Games as White: {summary['v7p3r_as_white']}
- Games as Black: {summary['v7p3r_as_black']}

---

## Problematic Openings

Openings where v7p3r committed the most errors:

"""
    
    openings = patterns["opening_patterns"]
    sorted_openings = sorted(
        openings.items(),
        key=lambda x: x[1]["blunders"] + x[1]["mistakes"],
        reverse=True
    )[:10]
    
    content += "| Opening | Games | Blunders | Mistakes | Total Errors |\n"
    content += "|---------|-------|----------|----------|-------------|\n"
    
    for opening, stats in sorted_openings:
        total_errors = stats["blunders"] + stats["mistakes"]
        content += f"| {opening[:60]} | {stats['games']} | {stats['blunders']} | {stats['mistakes']} | {total_errors} |\n"
    
    content += "\n---\n\n## Error Distribution by Game Phase\n\n"
    content += "| Move Range | Blunders | Mistakes | Total |\n"
    content += "|------------|----------|----------|---------|\n"
    
    move_patterns = sorted(patterns["move_number_patterns"].items())[:10]
    for move_range, stats in move_patterns:
        content += f"| Moves {move_range}-{move_range+4} | {stats['blunders']} | {stats['mistakes']} | {stats['blunders'] + stats['mistakes']} |\n"
    
    content += "\n---\n\n## Recommendations\n\n"
    
    # Generate recommendations based on patterns
    if move_patterns:
        worst_phase = max(move_patterns, key=lambda x: x[1]["blunders"] + x[1]["mistakes"])
        content += f"1. **Focus on moves {worst_phase[0]}-{worst_phase[0]+4}** — this phase shows the highest error rate\n"
    
    if sorted_openings:
        worst_opening = sorted_openings[0][0]
        content += f"2. **Review opening repertoire** — highest errors in: {worst_opening}\n"
    
    content += f"3. **Tactical training** — {v7p3r['blunders_per_game']:.2f} blunders per game indicates tactical oversights\n"
    content += f"4. **Accuracy target** — aim to improve from {summary['v7p3r_avg_accuracy']:.1f}% to 85%+ through focused training\n"
    
    content += "\n---\n\n## Next Steps\n\n"
    content += "- Review specific games with high error counts\n"
    content += "- Analyze common tactical patterns in blunders\n"
    content += "- Targeted opening preparation for problematic lines\n"
    content += "- Consider adjusting evaluation weights in weak phases\n"
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    
    console.print(f"[green]✓[/green] Markdown report saved to: [cyan]{path}[/cyan]")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze all 2026 v7p3r games with Stockfish")
    parser.add_argument("--depth", type=int, default=18, help="Stockfish depth (default: 18)")
    parser.add_argument("--quick", action="store_true", help="Use depth 15 for faster analysis")
    parser.add_argument("--max-games", type=int, help="Limit number of games to analyze")
    
    args = parser.parse_args()
    
    if not DEPS_AVAILABLE:
        return 1
    
    depth = 15 if args.quick else args.depth
    
    console.print("[bold cyan]v7p3r YTD 2026 Game Analysis[/bold cyan]")
    console.print(f"Stockfish depth: [yellow]{depth}[/yellow]")
    if args.max_games:
        console.print(f"Max games: [yellow]{args.max_games}[/yellow]")
    console.print()
    
    # Load games
    console.print("[cyan]Loading 2026 games...[/cyan]")
    games = load_all_2026_games(max_games=args.max_games)
    
    if not games:
        console.print("[red]No games found. Exiting.[/red]")
        return 1
    
    console.print(f"[green]✓[/green] Loaded {len(games)} games\n")
    
    # Analyze
    results = analyze_games_batch(games, depth=depth)
    
    if not results:
        console.print("[red]No successful analyses. Exiting.[/red]")
        return 1
    
    console.print(f"[green]✓[/green] Analyzed {len(results)} games successfully\n")
    
    # Aggregate patterns
    console.print("[cyan]Extracting patterns...[/cyan]")
    patterns = aggregate_patterns(results)
    console.print("[green]✓[/green] Pattern extraction complete\n")
    
    # Generate reports
    print_summary_report(patterns)
    save_results(results, patterns, depth)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
