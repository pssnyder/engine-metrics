"""
V7P3R Chess Engine - Gameplay Metrics Reporting Script
Analyzes conformed game dataset and generates insights reports
"""

import csv
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
import statistics


# Define base paths
BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "reporting_datasets"
REPORTS_DIR = BASE_DIR / "reports"
DATASET_FILE = DATASET_DIR / "v7p3r_game_data_latest.csv"


class GameDataset:
    """Loads and provides access to game data"""
    
    def __init__(self, csv_path: Path):
        self.games = []
        self.load_data(csv_path)
    
    def load_data(self, path: Path):
        """Load game data from CSV"""
        if not path.exists():
            print(f"Error: Dataset not found at {path}")
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.games = list(reader)
        
        print(f"Loaded {len(self.games)} games from dataset")
    
    def filter_by_date_range(self, start_date: str = None, end_date: str = None):
        """Filter games by date range (YYYY-MM-DD format)"""
        filtered = self.games
        
        if start_date:
            filtered = [g for g in filtered if g['date'].replace('.', '-') >= start_date]
        if end_date:
            filtered = [g for g in filtered if g['date'].replace('.', '-') <= end_date]
        
        return filtered
    
    def filter_by_version(self, version: str):
        """Filter games by engine version"""
        return [g for g in self.games if g['engine_version'] == version]
    
    def filter_recent(self, days: int):
        """Get games from the last N days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return self.filter_by_date_range(start_date=cutoff_date)


class MetricsCalculator:
    """Calculate various gameplay metrics"""
    
    @staticmethod
    def calculate_win_rates(games: List[Dict]) -> Dict:
        """Calculate overall and color-specific win rates"""
        if not games:
            return {}
        
        total = len(games)
        wins = sum(1 for g in games if g['outcome'] == 'win')
        losses = sum(1 for g in games if g['outcome'] == 'loss')
        draws = sum(1 for g in games if g['outcome'] == 'draw')
        
        # Color-specific metrics
        white_games = [g for g in games if g['color'] == 'white']
        black_games = [g for g in games if g['color'] == 'black']
        
        white_wins = sum(1 for g in white_games if g['outcome'] == 'win')
        black_wins = sum(1 for g in black_games if g['outcome'] == 'win')
        
        return {
            'total_games': total,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': round(wins / total * 100, 2) if total > 0 else 0,
            'loss_rate': round(losses / total * 100, 2) if total > 0 else 0,
            'draw_rate': round(draws / total * 100, 2) if total > 0 else 0,
            'white_games': len(white_games),
            'white_wins': white_wins,
            'white_win_rate': round(white_wins / len(white_games) * 100, 2) if white_games else 0,
            'black_games': len(black_games),
            'black_wins': black_wins,
            'black_win_rate': round(black_wins / len(black_games) * 100, 2) if black_games else 0,
        }
    
    @staticmethod
    def calculate_elo_stats(games: List[Dict]) -> Dict:
        """Calculate ELO-related statistics"""
        if not games:
            return {}
        
        elos = [int(g['v7p3r_elo']) for g in games if g['v7p3r_elo']]
        opponent_elos = [int(g['opponent_elo']) for g in games if g['opponent_elo']]
        rating_diffs = [int(g['rating_diff']) for g in games if g['rating_diff']]
        
        return {
            'current_elo': elos[-1] if elos else 0,
            'avg_elo': round(statistics.mean(elos), 2) if elos else 0,
            'min_elo': min(elos) if elos else 0,
            'max_elo': max(elos) if elos else 0,
            'avg_opponent_elo': round(statistics.mean(opponent_elos), 2) if opponent_elos else 0,
            'total_rating_change': sum(rating_diffs),
            'avg_rating_change': round(statistics.mean(rating_diffs), 2) if rating_diffs else 0,
        }
    
    @staticmethod
    def calculate_time_control_performance(games: List[Dict]) -> Dict:
        """Analyze performance by time control"""
        time_controls = defaultdict(lambda: {'games': 0, 'wins': 0, 'losses': 0, 'draws': 0})
        
        for game in games:
            tc = game['time_control']
            time_controls[tc]['games'] += 1
            if game['outcome'] == 'win':
                time_controls[tc]['wins'] += 1
            elif game['outcome'] == 'loss':
                time_controls[tc]['losses'] += 1
            elif game['outcome'] == 'draw':
                time_controls[tc]['draws'] += 1
        
        # Calculate win rates
        tc_stats = {}
        for tc, stats in time_controls.items():
            tc_stats[tc] = {
                **stats,
                'win_rate': round(stats['wins'] / stats['games'] * 100, 2) if stats['games'] > 0 else 0
            }
        
        # Sort by number of games
        tc_stats = dict(sorted(tc_stats.items(), key=lambda x: x[1]['games'], reverse=True))
        
        return tc_stats
    
    @staticmethod
    def calculate_opening_performance(games: List[Dict], top_n: int = 10) -> Dict:
        """Analyze performance by opening"""
        openings = defaultdict(lambda: {'games': 0, 'wins': 0, 'losses': 0, 'draws': 0})
        
        for game in games:
            opening = game['opening'] or game['eco'] or 'Unknown'
            openings[opening]['games'] += 1
            if game['outcome'] == 'win':
                openings[opening]['wins'] += 1
            elif game['outcome'] == 'loss':
                openings[opening]['losses'] += 1
            elif game['outcome'] == 'draw':
                openings[opening]['draws'] += 1
        
        # Calculate win rates
        opening_stats = {}
        for opening, stats in openings.items():
            opening_stats[opening] = {
                **stats,
                'win_rate': round(stats['wins'] / stats['games'] * 100, 2) if stats['games'] > 0 else 0
            }
        
        # Get top N by games played
        top_openings = dict(sorted(opening_stats.items(), 
                                  key=lambda x: x[1]['games'], 
                                  reverse=True)[:top_n])
        
        return top_openings
    
    @staticmethod
    def calculate_termination_stats(games: List[Dict]) -> Dict:
        """Analyze how games end"""
        terminations = Counter(g['termination'] for g in games)
        total = len(games)
        
        return {
            term: {
                'count': count,
                'percentage': round(count / total * 100, 2)
            }
            for term, count in terminations.most_common()
        }
    
    @staticmethod
    def calculate_version_comparison(games: List[Dict]) -> Dict:
        """Compare performance across engine versions"""
        versions = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'elo_changes': [], 'move_counts': []
        })
        
        for game in games:
            ver = game['engine_version']
            versions[ver]['games'] += 1
            
            if game['outcome'] == 'win':
                versions[ver]['wins'] += 1
            elif game['outcome'] == 'loss':
                versions[ver]['losses'] += 1
            elif game['outcome'] == 'draw':
                versions[ver]['draws'] += 1
            
            if game['rating_diff']:
                versions[ver]['elo_changes'].append(int(game['rating_diff']))
            
            if game['move_count']:
                try:
                    versions[ver]['move_counts'].append(int(game['move_count']))
                except ValueError:
                    pass
        
        # Calculate stats
        version_stats = {}
        for ver, data in versions.items():
            total = data['games']
            version_stats[ver] = {
                'games': total,
                'wins': data['wins'],
                'losses': data['losses'],
                'draws': data['draws'],
                'win_rate': round(data['wins'] / total * 100, 2) if total > 0 else 0,
                'loss_rate': round(data['losses'] / total * 100, 2) if total > 0 else 0,
                'draw_rate': round(data['draws'] / total * 100, 2) if total > 0 else 0,
                'avg_elo_change': round(statistics.mean(data['elo_changes']), 2) if data['elo_changes'] else 0,
                'avg_moves': round(statistics.mean(data['move_counts']), 2) if data['move_counts'] else 0,
            }
        
        # Sort by games played
        version_stats = dict(sorted(version_stats.items(), 
                                   key=lambda x: x[1]['games'], 
                                   reverse=True))
        
        return version_stats


class ReportGenerator:
    """Generate formatted reports"""
    
    def __init__(self, dataset: GameDataset):
        self.dataset = dataset
        self.calc = MetricsCalculator()
    
    def generate_recent_gameplay_report(self, days: int = 30, output_file: Path = None):
        """Generate report for recent gameplay"""
        recent_games = self.dataset.filter_recent(days)
        
        if not recent_games:
            print(f"No games found in the last {days} days")
            return
        
        # Calculate all metrics
        win_rates = self.calc.calculate_win_rates(recent_games)
        elo_stats = self.calc.calculate_elo_stats(recent_games)
        tc_performance = self.calc.calculate_time_control_performance(recent_games)
        opening_performance = self.calc.calculate_opening_performance(recent_games, top_n=10)
        terminations = self.calc.calculate_termination_stats(recent_games)
        
        # Build report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"V7P3R Chess Engine - Recent Gameplay Metrics Report")
        report_lines.append(f"Period: Last {days} Days")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Overall Performance
        report_lines.append("## OVERALL PERFORMANCE")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Games: {win_rates['total_games']}")
        report_lines.append(f"Record: {win_rates['wins']}W - {win_rates['losses']}L - {win_rates['draws']}D")
        report_lines.append(f"Win Rate: {win_rates['win_rate']}%")
        report_lines.append(f"Loss Rate: {win_rates['loss_rate']}%")
        report_lines.append(f"Draw Rate: {win_rates['draw_rate']}%")
        report_lines.append("")
        
        # Color Performance
        report_lines.append("## COLOR PERFORMANCE")
        report_lines.append("-" * 80)
        report_lines.append(f"White Games: {win_rates['white_games']} ({win_rates['white_wins']} wins)")
        report_lines.append(f"White Win Rate: {win_rates['white_win_rate']}%")
        report_lines.append(f"Black Games: {win_rates['black_games']} ({win_rates['black_wins']} wins)")
        report_lines.append(f"Black Win Rate: {win_rates['black_win_rate']}%")
        
        color_balance = win_rates['white_win_rate'] - win_rates['black_win_rate']
        report_lines.append(f"Color Balance: {abs(color_balance):.2f}% {'(White stronger)' if color_balance > 0 else '(Black stronger)' if color_balance < 0 else '(Balanced)'}")
        report_lines.append("")
        
        # ELO Statistics
        report_lines.append("## ELO STATISTICS")
        report_lines.append("-" * 80)
        report_lines.append(f"Current ELO: {elo_stats['current_elo']}")
        report_lines.append(f"Average ELO: {elo_stats['avg_elo']}")
        report_lines.append(f"ELO Range: {elo_stats['min_elo']} - {elo_stats['max_elo']}")
        report_lines.append(f"Total Rating Change: {elo_stats['total_rating_change']:+d}")
        report_lines.append(f"Avg Rating Change/Game: {elo_stats['avg_rating_change']:+.2f}")
        report_lines.append(f"Avg Opponent ELO: {elo_stats['avg_opponent_elo']}")
        report_lines.append("")
        
        # Time Control Performance
        report_lines.append("## TIME CONTROL PERFORMANCE")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Time Control':<15} {'Games':<8} {'Record':<15} {'Win Rate':<10}")
        report_lines.append("-" * 80)
        for tc, stats in tc_performance.items():
            record = f"{stats['wins']}W-{stats['losses']}L-{stats['draws']}D"
            report_lines.append(f"{tc:<15} {stats['games']:<8} {record:<15} {stats['win_rate']:.2f}%")
        report_lines.append("")
        
        # Top Openings
        report_lines.append("## TOP 10 OPENINGS")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Opening':<45} {'Games':<8} {'Record':<15} {'Win Rate':<10}")
        report_lines.append("-" * 80)
        for opening, stats in opening_performance.items():
            record = f"{stats['wins']}W-{stats['losses']}L-{stats['draws']}D"
            opening_short = opening[:43] + ".." if len(opening) > 45 else opening
            report_lines.append(f"{opening_short:<45} {stats['games']:<8} {record:<15} {stats['win_rate']:.2f}%")
        report_lines.append("")
        
        # Termination Stats
        report_lines.append("## GAME TERMINATIONS")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Termination Type':<30} {'Count':<10} {'Percentage':<10}")
        report_lines.append("-" * 80)
        for term, stats in terminations.items():
            report_lines.append(f"{term:<30} {stats['count']:<10} {stats['percentage']:.2f}%")
        report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("End of Report")
        report_lines.append("=" * 80)
        
        # Save report
        report_text = "\n".join(report_lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')
            print(f"\n✓ Report saved to: {output_file}")
        
        return report_text
    
    def generate_version_comparison_report(self, output_file: Path = None):
        """Generate version comparison report"""
        all_games = self.dataset.games
        version_stats = self.calc.calculate_version_comparison(all_games)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"V7P3R Chess Engine - Version Performance Comparison")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        report_lines.append("## VERSION PERFORMANCE METRICS")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Version':<12} {'Games':<8} {'Win Rate':<10} {'Loss Rate':<10} {'Draw Rate':<10} {'Avg ELO∆':<10} {'Avg Moves':<10}")
        report_lines.append("-" * 80)
        
        for version, stats in version_stats.items():
            report_lines.append(
                f"{version:<12} {stats['games']:<8} "
                f"{stats['win_rate']:<10.2f} {stats['loss_rate']:<10.2f} {stats['draw_rate']:<10.2f} "
                f"{stats['avg_elo_change']:<+10.2f} {stats['avg_moves']:<10.2f}"
            )
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')
            print(f"✓ Version comparison report saved to: {output_file}")
        
        return report_text


def main():
    """Main reporting pipeline"""
    print("=" * 80)
    print("V7P3R Chess Engine - Gameplay Metrics Reporting")
    print("=" * 80)
    print()
    
    # Load dataset
    print("Loading game dataset...")
    dataset = GameDataset(DATASET_FILE)
    print()
    
    if not dataset.games:
        print("No data available. Please run extract_game_data.py first.")
        return
    
    # Initialize report generator
    report_gen = ReportGenerator(dataset)
    
    # Generate recent gameplay report (last 30 days)
    print("Generating Recent Gameplay Report (Last 30 Days)...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    recent_report_file = REPORTS_DIR / f"v7p3r_recent_gameplay_report_{timestamp}.txt"
    recent_report = report_gen.generate_recent_gameplay_report(days=30, output_file=recent_report_file)
    
    # Also save as "latest"
    latest_report_file = REPORTS_DIR / "v7p3r_recent_gameplay_report_latest.txt"
    latest_report_file.write_text(recent_report, encoding='utf-8')
    print(f"  Also saved as: {latest_report_file}")
    print()
    
    # Generate version comparison report
    print("Generating Version Comparison Report...")
    version_report_file = REPORTS_DIR / f"v7p3r_version_comparison_report_{timestamp}.txt"
    report_gen.generate_version_comparison_report(output_file=version_report_file)
    
    latest_version_file = REPORTS_DIR / "v7p3r_version_comparison_report_latest.txt"
    report_gen.generate_version_comparison_report(output_file=latest_version_file)
    print(f"  Also saved as: {latest_version_file}")
    print()
    
    print("=" * 80)
    print("Reporting Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
