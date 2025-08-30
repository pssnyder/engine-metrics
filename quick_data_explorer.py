"""
Quick Data Explorer for Chess Engine Analysis
Run this script to get an immediate overview of your data.
"""

import pandas as pd
import json
import chess.pgn
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import sys

# Set up plotting for dark theme
plt.style.use('dark_background')
sns.set_theme(style="darkgrid")

class ChessDataExplorer:
    def __init__(self, game_records_path="game_records", engine_tester_path="engine-tester"):
        self.game_records_path = Path(game_records_path)
        self.engine_tester_path = Path(engine_tester_path)
        self.pgn_data = None
        self.json_data = {}
    
    def scan_data_files(self):
        """Scan and inventory all available data files."""
        print("=== DATA INVENTORY ===")
        
        # PGN files
        pgn_files = list(self.game_records_path.glob("**/*.pgn"))
        print(f"📁 Found {len(pgn_files)} PGN files")
        
        # Show file sizes
        pgn_sizes = []
        for pgn in pgn_files[:10]:  # Show first 10
            size = pgn.stat().st_size / 1024  # KB
            pgn_sizes.append((pgn.name, size))
            print(f"   {pgn.name}: {size:.1f} KB")
        
        if len(pgn_files) > 10:
            print(f"   ... and {len(pgn_files) - 10} more files")
        
        # JSON analysis files
        json_files = list(self.engine_tester_path.glob("**/*.json"))
        print(f"\n📊 Found {len(json_files)} JSON analysis files")
        
        for json_file in json_files[:15]:  # Show first 15
            size = json_file.stat().st_size / 1024  # KB
            print(f"   {json_file.name}: {size:.1f} KB")
        
        if len(json_files) > 15:
            print(f"   ... and {len(json_files) - 15} more files")
        
        return pgn_files, json_files
    
    def quick_pgn_analysis(self, num_files=3):
        """Quick analysis of recent PGN files."""
        print("\n=== QUICK PGN ANALYSIS ===")
        
        pgn_files = sorted(self.game_records_path.glob("**/*.pgn"))[-num_files:]
        all_games = []
        
        for pgn_file in pgn_files:
            print(f"\nAnalyzing: {pgn_file.name}")
            try:
                games = self.parse_pgn_file(pgn_file)
                all_games.extend(games)
                print(f"   Games found: {len(games)}")
                
                if games:
                    df = pd.DataFrame(games)
                    engines = set(df['white'].tolist() + df['black'].tolist())
                    print(f"   Engines: {', '.join(sorted(engines))}")
                    print(f"   Results: {df['result'].value_counts().to_dict()}")
                    
            except Exception as e:
                print(f"   Error reading file: {e}")
        
        if all_games:
            self.pgn_data = pd.DataFrame(all_games)
            self.analyze_combined_pgn_data()
        
        return all_games
    
    def parse_pgn_file(self, pgn_path):
        """Parse a single PGN file and extract game data."""
        games = []
        
        try:
            with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    games.append({
                        'white': game.headers.get('White', ''),
                        'black': game.headers.get('Black', ''),
                        'result': game.headers.get('Result', ''),
                        'date': game.headers.get('Date', ''),
                        'event': game.headers.get('Event', ''),
                        'plycount': int(game.headers.get('PlyCount', 0)) if game.headers.get('PlyCount', '').isdigit() else 0,
                        'time_control': game.headers.get('TimeControl', ''),
                        'termination': game.headers.get('Termination', ''),
                        'file': pgn_path.name
                    })
        except Exception as e:
            print(f"Error parsing {pgn_path}: {e}")
        
        return games
    
    def analyze_combined_pgn_data(self):
        """Analyze the combined PGN data."""
        if self.pgn_data is None or len(self.pgn_data) == 0:
            return
        
        print("\n=== COMBINED ANALYSIS ===")
        print(f"Total games analyzed: {len(self.pgn_data)}")
        
        # Engine analysis
        all_engines = set(self.pgn_data['white'].tolist() + self.pgn_data['black'].tolist())
        print(f"Unique engines: {len(all_engines)}")
        for engine in sorted(all_engines):
            print(f"   {engine}")
        
        # Result distribution
        print(f"\nResult distribution:")
        results = self.pgn_data['result'].value_counts()
        for result, count in results.items():
            percentage = (count / len(self.pgn_data)) * 100
            print(f"   {result}: {count} ({percentage:.1f}%)")
        
        # Game length analysis
        valid_lengths = self.pgn_data[self.pgn_data['plycount'] > 0]['plycount']
        if len(valid_lengths) > 0:
            print(f"\nGame lengths (plies):")
            print(f"   Average: {valid_lengths.mean():.1f}")
            print(f"   Median: {valid_lengths.median():.1f}")
            print(f"   Min: {valid_lengths.min()}")
            print(f"   Max: {valid_lengths.max()}")
        
        # Head-to-head analysis
        self.analyze_head_to_head()
    
    def analyze_head_to_head(self):
        """Analyze V7P3R vs SlowMate specifically."""
        if self.pgn_data is None:
            return
        
        print("\n=== HEAD-TO-HEAD ANALYSIS ===")
        
        # Find V7P3R vs SlowMate games
        h2h = self.pgn_data[
            ((self.pgn_data['white'].str.contains('v7p3r', case=False)) & 
             (self.pgn_data['black'].str.contains('slowmate', case=False))) |
            ((self.pgn_data['white'].str.contains('slowmate', case=False)) & 
             (self.pgn_data['black'].str.contains('v7p3r', case=False)))
        ]
        
        print(f"V7P3R vs SlowMate games: {len(h2h)}")
        
        if len(h2h) > 0:
            print("Results:")
            for result, count in h2h['result'].value_counts().items():
                print(f"   {result}: {count}")
            
            # Analyze by color
            v7p3r_white = h2h[h2h['white'].str.contains('v7p3r', case=False)]
            v7p3r_black = h2h[h2h['black'].str.contains('v7p3r', case=False)]
            
            print(f"\nV7P3R as White: {len(v7p3r_white)} games")
            if len(v7p3r_white) > 0:
                wins = len(v7p3r_white[v7p3r_white['result'] == '1-0'])
                print(f"   Wins: {wins}/{len(v7p3r_white)} ({wins/len(v7p3r_white)*100:.1f}%)")
            
            print(f"V7P3R as Black: {len(v7p3r_black)} games")
            if len(v7p3r_black) > 0:
                wins = len(v7p3r_black[v7p3r_black['result'] == '0-1'])
                print(f"   Wins: {wins}/{len(v7p3r_black)} ({wins/len(v7p3r_black)*100:.1f}%)")
    
    def explore_json_analysis(self, num_files=5):
        """Explore JSON analysis files."""
        print("\n=== JSON ANALYSIS EXPLORATION ===")
        
        json_files = list(self.engine_tester_path.glob("**/*.json"))[-num_files:]
        
        for json_file in json_files:
            print(f"\nExploring: {json_file.name}")
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                print(f"   Type: {type(data)}")
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                    
                    # Look for interesting data
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            print(f"   {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"   {key}: {len(value)} keys")
                        else:
                            print(f"   {key}: {value}")
                
                self.json_data[json_file.name] = data
                
            except Exception as e:
                print(f"   Error reading file: {e}")
    
    def create_quick_visualizations(self):
        """Create some quick visualizations."""
        if self.pgn_data is None or len(self.pgn_data) == 0:
            print("\nNo PGN data available for visualization")
            return
        
        print("\n=== CREATING VISUALIZATIONS ===")
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Chess Engine Data Overview', fontsize=16)
            
            # Result distribution
            self.pgn_data['result'].value_counts().plot(kind='bar', ax=axes[0,0])
            axes[0,0].set_title('Game Results Distribution')
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # Game lengths
            valid_lengths = self.pgn_data[self.pgn_data['plycount'] > 0]['plycount']
            if len(valid_lengths) > 0:
                valid_lengths.hist(bins=30, ax=axes[0,1])
                axes[0,1].set_title('Game Length Distribution (Plies)')
                axes[0,1].set_xlabel('Plies')
            
            # Engine frequency
            all_engines = list(self.pgn_data['white']) + list(self.pgn_data['black'])
            engine_counts = pd.Series(all_engines).value_counts().head(10)
            engine_counts.plot(kind='barh', ax=axes[1,0])
            axes[1,0].set_title('Top 10 Most Active Engines')
            
            # Files analyzed
            self.pgn_data['file'].value_counts().plot(kind='bar', ax=axes[1,1])
            axes[1,1].set_title('Games per File')
            axes[1,1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.savefig('chess_data_overview.png', dpi=150, bbox_inches='tight')
            print("Visualization saved as 'chess_data_overview.png'")
            plt.show()
            
        except Exception as e:
            print(f"Error creating visualizations: {e}")
    
    def export_summary_data(self):
        """Export summary data for further analysis."""
        if self.pgn_data is not None:
            # Export to CSV for Excel/other tools
            self.pgn_data.to_csv('chess_games_summary.csv', index=False)
            print("\nExported game data to 'chess_games_summary.csv'")
            
            # Create engine performance summary
            engine_performance = []
            all_engines = set(self.pgn_data['white'].tolist() + self.pgn_data['black'].tolist())
            
            for engine in all_engines:
                white_games = self.pgn_data[self.pgn_data['white'] == engine]
                black_games = self.pgn_data[self.pgn_data['black'] == engine]
                
                white_wins = len(white_games[white_games['result'] == '1-0'])
                black_wins = len(black_games[black_games['result'] == '0-1'])
                total_games = len(white_games) + len(black_games)
                
                engine_performance.append({
                    'engine': engine,
                    'total_games': total_games,
                    'wins': white_wins + black_wins,
                    'win_rate': (white_wins + black_wins) / total_games if total_games > 0 else 0,
                    'games_as_white': len(white_games),
                    'games_as_black': len(black_games)
                })
            
            perf_df = pd.DataFrame(engine_performance)
            perf_df.to_csv('engine_performance_summary.csv', index=False)
            print("Exported performance data to 'engine_performance_summary.csv'")

def main():
    print("🔍 Chess Engine Data Explorer")
    print("=============================")
    
    explorer = ChessDataExplorer()
    
    # Step 1: Scan available data
    pgn_files, json_files = explorer.scan_data_files()
    
    if not pgn_files and not json_files:
        print("❌ No data files found. Please check your paths.")
        return
    
    # Step 2: Quick PGN analysis
    if pgn_files:
        explorer.quick_pgn_analysis(num_files=min(5, len(pgn_files)))
    
    # Step 3: JSON exploration
    if json_files:
        explorer.explore_json_analysis(num_files=min(3, len(json_files)))
    
    # Step 4: Visualizations
    if explorer.pgn_data is not None:
        explorer.create_quick_visualizations()
        explorer.export_summary_data()
    
    print("\n✅ Exploration complete!")
    print("Next steps:")
    print("1. Open 'chess_games_summary.csv' in Excel or VS Code")
    print("2. Review 'engine_performance_summary.csv' for detailed stats")
    print("3. Check 'chess_data_overview.png' for visual summary")
    print("4. Use the DATA_EXPLORATION_GUIDE.md for deeper analysis")

if __name__ == "__main__":
    main()
