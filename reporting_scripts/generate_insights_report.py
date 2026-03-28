"""
V7P3R Chess Engine - Multi-Dimensional Insights Analytics
Lichess-style "slice X by Y" analysis framework
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Any, Callable
import statistics


BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "reporting_datasets"
REPORTS_DIR = BASE_DIR / "reports" / "insights"

# Dataset files
GAME_DATA_FILE = DATASET_DIR / "v7p3r_game_data_latest.csv"
MOVE_DATA_FILE = DATASET_DIR / "v7p3r_moves_latest.csv"
SUMMARY_DATA_FILE = DATASET_DIR / "v7p3r_game_summary_enhanced_latest.csv"


class DataLoader:
    """Load and cache datasets"""
    
    def __init__(self):
        self.games = []
        self.moves = []
        self.summaries = {}
        self.load_all()
    
    def load_all(self):
        """Load all datasets"""
        print("Loading datasets...")
        
        # Load game metadata
        if GAME_DATA_FILE.exists():
            with open(GAME_DATA_FILE, 'r', encoding='utf-8') as f:
                self.games = list(csv.DictReader(f))
            print(f"  Loaded {len(self.games)} games")
        
        # Load enhanced summaries
        if SUMMARY_DATA_FILE.exists():
            with open(SUMMARY_DATA_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.summaries = {row['game_id']: row for row in reader}
            print(f"  Loaded {len(self.summaries)} game summaries")
        
        # Merge summaries into games
        for game in self.games:
            game_id = game['game_id']
            if game_id in self.summaries:
                game.update(self.summaries[game_id])
        
        print()
    
    def load_moves_sample(self, max_moves: int = None):
        """Load move-level data (optionally limited for performance)"""
        if not MOVE_DATA_FILE.exists():
            print("Move data not found")
            return
        
        print(f"Loading move data{'(sampling)' if max_moves else ''}...")
        with open(MOVE_DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if max_moves:
                import itertools
                self.moves = list(itertools.islice(reader, max_moves))
            else:
                self.moves = list(reader)
        
        print(f"  Loaded {len(self.moves)} moves\n")


class DimensionBuckets:
    """Define dimension bucketing strategies"""
    
    @staticmethod
    def opponent_strength(opponent_elo: str) -> str:
        """Bucket opponent by ELO"""
        try:
            elo = int(opponent_elo)
        except (ValueError, TypeError):
            return "Unknown"
        
        if elo < 1400:
            return "<1400"
        elif elo < 1600:
            return "1400-1600"
        elif elo < 1800:
            return "1600-1800"
        elif elo < 2000:
            return "1800-2000"
        elif elo < 2200:
            return "2000-2200"
        else:
            return "2200+"
    
    @staticmethod
    def time_control_category(time_control: str) -> str:
        """Categorize time control"""
        if not time_control:
            return "Unknown"
        
        try:
            # Parse "seconds+increment"
            parts = time_control.split('+')
            base = int(parts[0])
            
            if base < 180:
                return "Bullet (<3min)"
            elif base < 480:
                return "Blitz (3-8min)"
            elif base < 1500:
                return "Rapid (8-25min)"
            else:
                return "Classical (25min+)"
        except (ValueError, IndexError):
            return "Unknown"
    
    @staticmethod
    def game_result_simple(outcome: str) -> str:
        """Simplify result"""
        return outcome.capitalize() if outcome in ['win', 'loss', 'draw'] else 'Unknown'
    
    @staticmethod
    def date_period(date_str: str, period: str = 'month') -> str:
        """Bucket by time period"""
        try:
            date = datetime.strptime(date_str.replace('.', '-'), '%Y-%m-%d')
            
            if period == 'month':
                return date.strftime('%Y-%m')
            elif period == 'week':
                return date.strftime('%Y-W%U')
            elif period == 'day':
                return date.strftime('%Y-%m-%d')
            else:
                return date.strftime('%Y')
        except (ValueError, AttributeError):
            return "Unknown"


class InsightsEngine:
    """Core analytics engine for multi-dimensional analysis"""
    
    def __init__(self, data_loader: DataLoader):
        self.data = data_loader
        self.buckets = DimensionBuckets()
    
    def slice_by(self, dimension: str, games: List[Dict] = None) -> Dict[str, List[Dict]]:
        """Group games by a dimension"""
        if games is None:
            games = self.data.games
        
        slices = defaultdict(list)
        
        for game in games:
            # Determine bucket based on dimension
            if dimension == 'color':
                key = game.get('color', 'Unknown')
            elif dimension == 'opponent_strength':
                key = self.buckets.opponent_strength(game.get('opponent_elo', '0'))
            elif dimension == 'time_control_category':
                key = self.buckets.time_control_category(game.get('time_control', ''))
            elif dimension == 'result':
                key = self.buckets.game_result_simple(game.get('outcome', ''))
            elif dimension == 'opening_family':
                key = game.get('opening_family', 'Unknown')
            elif dimension == 'v7p3r_castled':
                key = game.get('v7p3r_castled', 'No castling')
            elif dimension == 'opponent_castled':
                key = game.get('opponent_castled', 'No castling')
            elif dimension == 'queen_traded':
                key = 'Queens traded' if game.get('queen_traded') == 'True' else 'Queens maintained'
            elif dimension == 'engine_version':
                key = game.get('engine_version', 'Unknown')
            elif dimension == 'termination':
                key = game.get('termination', 'Unknown')
            elif dimension == 'month':
                key = self.buckets.date_period(game.get('date', ''), period='month')
            elif dimension == 'event':
                key = game.get('event', 'Unknown')
            else:
                # Direct field lookup
                key = game.get(dimension, 'Unknown')
            
            slices[key].append(game)
        
        return dict(slices)
    
    def calculate_metrics(self, games: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate metrics for a set of games"""
        if not games:
            return {}
        
        total = len(games)
        wins = sum(1 for g in games if g.get('outcome') == 'win')
        losses = sum(1 for g in games if g.get('outcome') == 'loss')
        draws = sum(1 for g in games if g.get('outcome') == 'draw')
        
        # ELO stats
        elos = [int(g['v7p3r_elo']) for g in games if g.get('v7p3r_elo')]
        rating_diffs = [int(g['rating_diff']) for g in games if g.get('rating_diff')]
        
        # Move counts
        move_counts = []
        for g in games:
            try:
                move_counts.append(int(g.get('total_moves', g.get('move_count', 0))))
            except (ValueError, TypeError):
                pass
        
        return {
            'total_games': total,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': round(wins / total * 100, 2) if total > 0 else 0,
            'loss_rate': round(losses / total * 100, 2) if total > 0 else 0,
            'draw_rate': round(draws / total * 100, 2) if total > 0 else 0,
            'avg_elo': round(statistics.mean(elos), 2) if elos else 0,
            'avg_rating_change': round(statistics.mean(rating_diffs), 2) if rating_diffs else 0,
            'avg_game_length': round(statistics.mean(move_counts), 2) if move_counts else 0,
        }
    
    def multi_dimensional_analysis(self, primary_dim: str, secondary_dim: str = None,
                                   metric: str = 'win_rate', games: List[Dict] = None) -> Dict:
        """
        Perform multi-dimensional analysis (slice X by Y)
        
        Args:
            primary_dim: Primary dimension to slice by (e.g., 'opponent_strength')
            secondary_dim: Optional secondary dimension (e.g., 'color')
            metric: Metric to retrieve ('win_rate', 'total_games', 'avg_game_length', etc.)
            games: Optional filtered game set
        
        Returns:
            Nested dictionary of results
        """
        if games is None:
            games = self.data.games
        
        # Slice by primary dimension
        primary_slices = self.slice_by(primary_dim, games)
        
        results = {}
        
        for primary_key, primary_games in primary_slices.items():
            if not secondary_dim:
                # Single dimension analysis
                metrics = self.calculate_metrics(primary_games)
                results[primary_key] = metrics.get(metric, 0)
            else:
                # Two-dimensional analysis
                secondary_slices = self.slice_by(secondary_dim, primary_games)
                results[primary_key] = {}
                
                for secondary_key, secondary_games in secondary_slices.items():
                    metrics = self.calculate_metrics(secondary_games)
                    results[primary_key][secondary_key] = metrics.get(metric, 0)
        
        return results
    
    def top_n_analysis(self, dimension: str, metric: str = 'win_rate',
                      n: int = 10, games: List[Dict] = None) -> List[Tuple[str, float]]:
        """Get top N performers in a dimension"""
        if games is None:
            games = self.data.games
        
        slices = self.slice_by(dimension, games)
        
        results = []
        for key, slice_games in slices.items():
            metrics = self.calculate_metrics(slice_games)
            value = metrics.get(metric, 0)
            results.append((key, value, metrics['total_games']))
        
        # Sort by metric value, then filter by minimum games
        results = [(k, v, g) for k, v, g in results if g >= 5]  # Min 5 games
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:n]


class InsightsReportGenerator:
    """Generate formatted insights reports"""
    
    def __init__(self, engine: InsightsEngine):
        self.engine = engine
    
    def generate_comprehensive_report(self, output_file: Path = None):
        """Generate a comprehensive insights report"""
        lines = []
        lines.append("=" * 80)
        lines.append("V7P3R Chess Engine - Comprehensive Insights Report")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Games: {len(self.engine.data.games)}")
        lines.append("=" * 80)
        lines.append("")
        
        # 1. Win Rate by Opponent Strength
        lines.append("## WIN RATE BY OPPONENT STRENGTH")
        lines.append("-" * 80)
        results = self.engine.multi_dimensional_analysis('opponent_strength', metric='win_rate')
        for strength, win_rate in sorted(results.items()):
            slices = self.engine.slice_by('opponent_strength')
            game_count = len(slices[strength])
            lines.append(f"{strength:<20} {win_rate:>6.2f}%   ({game_count} games)")
        lines.append("")
        
        # 2. Performance by Color and Time Control
        lines.append("## PERFORMANCE BY COLOR AND TIME CONTROL")
        lines.append("-" * 80)
        results = self.engine.multi_dimensional_analysis('color', 'time_control_category', 'win_rate')
        lines.append(f"{'Time Control':<25} {'White Win %':<12} {'Black Win %':<12}")
        lines.append("-" * 80)
        
        white_results = results.get('white', {})
        black_results = results.get('black', {})
        all_tcs = set(white_results.keys()) | set(black_results.keys())
        
        for tc in sorted(all_tcs):
            white_wr = white_results.get(tc, 0)
            black_wr = black_results.get(tc, 0)
            lines.append(f"{tc:<25} {white_wr:<12.2f} {black_wr:<12.2f}")
        lines.append("")
        
        # 3. Opening Family Performance
        lines.append("## TOP 10 OPENING FAMILIES BY WIN RATE")
        lines.append("-" * 80)
        top_openings = self.engine.top_n_analysis('opening_family', 'win_rate', n=10)
        lines.append(f"{'Opening Family':<40} {'Win Rate':<12} {'Games':<8}")
        lines.append("-" * 80)
        for opening, win_rate, games in top_openings:
            lines.append(f"{opening[:38]:<40} {win_rate:<12.2f} {games:<8}")
        lines.append("")
        
        # 4. Castling Analysis
        lines.append("## CASTLING PATTERN ANALYSIS")
        lines.append("-" * 80)
        castling_results = self.engine.multi_dimensional_analysis('v7p3r_castled', metric='win_rate')
        lines.append(f"{'Castling Side':<20} {'Win Rate':<12} {'Games':<8}")
        lines.append("-" * 80)
        slices = self.engine.slice_by('v7p3r_castled')
        for side, win_rate in castling_results.items():
            game_count = len(slices[side])
            lines.append(f"{side:<20} {win_rate:<12.2f} {game_count:<8}")
        lines.append("")
        
        # 5. Queen Trade Impact
        lines.append("## QUEEN TRADE IMPACT ON WIN RATE")
        lines.append("-" * 80)
        queen_results = self.engine.multi_dimensional_analysis('queen_traded', metric='win_rate')
        slices = self.engine.slice_by('queen_traded')
        for scenario, win_rate in queen_results.items():
            game_count = len(slices[scenario])
            lines.append(f"{scenario:<25} {win_rate:<12.2f} {game_count:<8}")
        lines.append("")
        
        # 6. Monthly Performance Trend
        lines.append("## MONTHLY PERFORMANCE TREND")
        lines.append("-" * 80)
        monthly_results = self.engine.multi_dimensional_analysis('month', metric='win_rate')
        lines.append(f"{'Month':<15} {'Win Rate':<12} {'Games':<8}")
        lines.append("-" * 80)
        slices = self.engine.slice_by('month')
        for month in sorted(monthly_results.keys(), reverse=True)[:12]:  # Last 12 months
            win_rate = monthly_results[month]
            game_count = len(slices[month])
            lines.append(f"{month:<15} {win_rate:<12.2f} {game_count:<8}")
        lines.append("")
        
        # 7. Version Comparison
        lines.append("## ENGINE VERSION PERFORMANCE")
        lines .append("-" * 80)
        version_results = self.engine.multi_dimensional_analysis('engine_version', metric='win_rate')
        slices = self.engine.slice_by('engine_version')
        lines.append(f"{'Version':<15} {'Win Rate':<12} {'Games':<8}")
        lines.append("-" * 80)
        for version in sorted(slices.keys(), key=lambda v: len(slices[v]), reverse=True):
            win_rate = version_results[version]
            game_count = len(slices[version])
            lines.append(f"{version:<15} {win_rate:<12.2f} {game_count:<8}")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("End of Insights Report")
        lines.append("=" * 80)
        
        report_text = "\n".join(lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')
            print(f"\n✓ Comprehensive insights report saved: {output_file}")
        
        return report_text


def main():
    """Main insights pipeline"""
    print("=" * 80)
    print("V7P3R Multi-Dimensional Insights Analytics")
    print("=" * 80)
    print()
    
    # Load data
    loader = DataLoader()
    
    if not loader.games:
        print("No game data found. Please run extract_game_data.py first.")
        return
    
    # Create insights engine
    engine = InsightsEngine(loader)
    
    # Generate comprehensive report
    report_gen = InsightsReportGenerator(engine)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = REPORTS_DIR / f"comprehensive_insights_{timestamp}.txt"
    
    print("Generating comprehensive insights report...\n")
    report_gen.generate_comprehensive_report(output_file=report_file)
    
    # Also save latest
    latest_file = REPORTS_DIR / "comprehensive_insights_latest.txt"
    report_gen.generate_comprehensive_report(output_file=latest_file)
    print(f"  Also saved as: {latest_file}")
    
    print()
    print("=" * 80)
    print("Insights Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
