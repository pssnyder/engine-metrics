"""
V7P3R vs SlowMate Head-to-Head Analysis Script
Specifically focused on the matchup you're most interested in.
"""

import pandas as pd
import chess.pgn
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import numpy as np

plt.style.use('dark_background')
sns.set_theme(style="darkgrid")

class HeadToHeadAnalyzer:
    def __init__(self, game_records_path="game_records"):
        self.game_records_path = Path(game_records_path)
        self.v7p3r_vs_slowmate = []
        self.engine_versions = {
            'v7p3r': set(),
            'slowmate': set()
        }
    
    def find_all_h2h_games(self):
        """Find all V7P3R vs SlowMate games across all PGN files."""
        print("🔍 Scanning for V7P3R vs SlowMate games...")
        
        pgn_files = list(self.game_records_path.glob("**/*.pgn"))
        total_games = 0
        
        for pgn_file in pgn_files:
            games = self.extract_h2h_from_file(pgn_file)
            self.v7p3r_vs_slowmate.extend(games)
            if games:
                print(f"   {pgn_file.name}: {len(games)} H2H games")
            total_games += len(games)
        
        print(f"\n📊 Total V7P3R vs SlowMate games found: {total_games}")
        return total_games
    
    def extract_h2h_from_file(self, pgn_path):
        """Extract V7P3R vs SlowMate games from a single PGN file."""
        games = []
        
        try:
            with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    white = game.headers.get('White', '').lower()
                    black = game.headers.get('Black', '').lower()
                    
                    # Check if this is a V7P3R vs SlowMate game
                    is_h2h = False
                    v7p3r_color = None
                    
                    if 'v7p3r' in white and 'slowmate' in black:
                        is_h2h = True
                        v7p3r_color = 'white'
                    elif 'slowmate' in white and 'v7p3r' in black:
                        is_h2h = True
                        v7p3r_color = 'black'
                    
                    if is_h2h:
                        # Track engine versions
                        if 'v7p3r' in white:
                            self.engine_versions['v7p3r'].add(game.headers.get('White', ''))
                            self.engine_versions['slowmate'].add(game.headers.get('Black', ''))
                        else:
                            self.engine_versions['v7p3r'].add(game.headers.get('Black', ''))
                            self.engine_versions['slowmate'].add(game.headers.get('White', ''))
                        
                        games.append({
                            'white': game.headers.get('White', ''),
                            'black': game.headers.get('Black', ''),
                            'result': game.headers.get('Result', ''),
                            'date': game.headers.get('Date', ''),
                            'event': game.headers.get('Event', ''),
                            'plycount': int(game.headers.get('PlyCount', 0)) if game.headers.get('PlyCount', '').isdigit() else 0,
                            'time_control': game.headers.get('TimeControl', ''),
                            'termination': game.headers.get('Termination', ''),
                            'v7p3r_color': v7p3r_color,
                            'file': pgn_path.name
                        })
        
        except Exception as e:
            print(f"Error parsing {pgn_path}: {e}")
        
        return games
    
    def analyze_overall_performance(self):
        """Analyze overall V7P3R vs SlowMate performance."""
        if not self.v7p3r_vs_slowmate:
            print("❌ No head-to-head games found!")
            return
        
        df = pd.DataFrame(self.v7p3r_vs_slowmate)
        
        print("\n=== OVERALL PERFORMANCE ===")
        print(f"Total games: {len(df)}")
        
        # Overall results
        print(f"\nResult breakdown:")
        for result, count in df['result'].value_counts().items():
            percentage = (count / len(df)) * 100
            print(f"   {result}: {count} ({percentage:.1f}%)")
        
        # V7P3R performance calculation
        v7p3r_wins = 0
        slowmate_wins = 0
        draws = 0
        
        for _, game in df.iterrows():
            result = game['result']
            v7p3r_color = game['v7p3r_color']
            
            if result == '1/2-1/2':
                draws += 1
            elif (result == '1-0' and v7p3r_color == 'white') or (result == '0-1' and v7p3r_color == 'black'):
                v7p3r_wins += 1
            elif (result == '0-1' and v7p3r_color == 'white') or (result == '1-0' and v7p3r_color == 'black'):
                slowmate_wins += 1
        
        total_decisive = v7p3r_wins + slowmate_wins
        
        print(f"\n🎯 HEAD-TO-HEAD SCORE:")
        print(f"   V7P3R wins: {v7p3r_wins}")
        print(f"   SlowMate wins: {slowmate_wins}")
        print(f"   Draws: {draws}")
        
        if total_decisive > 0:
            v7p3r_win_rate = (v7p3r_wins / total_decisive) * 100
            print(f"\n📈 V7P3R win rate (decisive games): {v7p3r_win_rate:.1f}%")
        
        overall_win_rate = (v7p3r_wins / len(df)) * 100
        print(f"📈 V7P3R win rate (all games): {overall_win_rate:.1f}%")
        
        return df
    
    def analyze_by_color(self, df):
        """Analyze performance by color."""
        print("\n=== PERFORMANCE BY COLOR ===")
        
        v7p3r_white = df[df['v7p3r_color'] == 'white']
        v7p3r_black = df[df['v7p3r_color'] == 'black']
        
        print(f"V7P3R as White: {len(v7p3r_white)} games")
        if len(v7p3r_white) > 0:
            white_wins = len(v7p3r_white[v7p3r_white['result'] == '1-0'])
            white_draws = len(v7p3r_white[v7p3r_white['result'] == '1/2-1/2'])
            white_losses = len(v7p3r_white[v7p3r_white['result'] == '0-1'])
            
            print(f"   Wins: {white_wins} ({white_wins/len(v7p3r_white)*100:.1f}%)")
            print(f"   Draws: {white_draws} ({white_draws/len(v7p3r_white)*100:.1f}%)")
            print(f"   Losses: {white_losses} ({white_losses/len(v7p3r_white)*100:.1f}%)")
        
        print(f"\nV7P3R as Black: {len(v7p3r_black)} games")
        if len(v7p3r_black) > 0:
            black_wins = len(v7p3r_black[v7p3r_black['result'] == '0-1'])
            black_draws = len(v7p3r_black[v7p3r_black['result'] == '1/2-1/2'])
            black_losses = len(v7p3r_black[v7p3r_black['result'] == '1-0'])
            
            print(f"   Wins: {black_wins} ({black_wins/len(v7p3r_black)*100:.1f}%)")
            print(f"   Draws: {black_draws} ({black_draws/len(v7p3r_black)*100:.1f}%)")
            print(f"   Losses: {black_losses} ({black_losses/len(v7p3r_black)*100:.1f}%)")
    
    def analyze_by_time_control(self, df):
        """Analyze performance by time control."""
        print("\n=== PERFORMANCE BY TIME CONTROL ===")
        
        time_controls = df['time_control'].value_counts()
        for tc, count in time_controls.items():
            print(f"\nTime Control: {tc} ({count} games)")
            
            tc_games = df[df['time_control'] == tc]
            v7p3r_wins = 0
            
            for _, game in tc_games.iterrows():
                result = game['result']
                v7p3r_color = game['v7p3r_color']
                
                if (result == '1-0' and v7p3r_color == 'white') or (result == '0-1' and v7p3r_color == 'black'):
                    v7p3r_wins += 1
            
            win_rate = (v7p3r_wins / len(tc_games)) * 100 if len(tc_games) > 0 else 0
            print(f"   V7P3R win rate: {win_rate:.1f}%")
    
    def analyze_game_lengths(self, df):
        """Analyze game length patterns."""
        print("\n=== GAME LENGTH ANALYSIS ===")
        
        valid_lengths = df[df['plycount'] > 0]['plycount']
        if len(valid_lengths) > 0:
            print(f"Average game length: {valid_lengths.mean():.1f} plies")
            print(f"Median game length: {valid_lengths.median():.1f} plies")
            print(f"Shortest game: {valid_lengths.min()} plies")
            print(f"Longest game: {valid_lengths.max()} plies")
            
            # Analyze by result
            for result in ['1-0', '0-1', '1/2-1/2']:
                result_games = df[df['result'] == result]
                result_lengths = result_games[result_games['plycount'] > 0]['plycount']
                if len(result_lengths) > 0:
                    print(f"\n{result} games:")
                    print(f"   Average: {result_lengths.mean():.1f} plies")
                    print(f"   Count: {len(result_lengths)}")
    
    def show_engine_versions(self):
        """Show all engine versions found."""
        print("\n=== ENGINE VERSIONS DETECTED ===")
        
        print("V7P3R versions:")
        for version in sorted(self.engine_versions['v7p3r']):
            print(f"   {version}")
        
        print("\nSlowMate versions:")
        for version in sorted(self.engine_versions['slowmate']):
            print(f"   {version}")
    
    def create_h2h_visualizations(self, df):
        """Create head-to-head specific visualizations."""
        print("\n=== CREATING H2H VISUALIZATIONS ===")
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('V7P3R vs SlowMate Head-to-Head Analysis', fontsize=16)
            
            # Overall results pie chart
            result_counts = df['result'].value_counts()
            axes[0,0].pie(result_counts.values, labels=result_counts.index, autopct='%1.1f%%')
            axes[0,0].set_title('Overall Results Distribution')
            
            # Performance by color
            color_performance = []
            colors = ['white', 'black']
            
            for color in colors:
                color_games = df[df['v7p3r_color'] == color]
                if len(color_games) > 0:
                    wins = 0
                    for _, game in color_games.iterrows():
                        result = game['result']
                        if (result == '1-0' and color == 'white') or (result == '0-1' and color == 'black'):
                            wins += 1
                    win_rate = (wins / len(color_games)) * 100
                    color_performance.append(win_rate)
                else:
                    color_performance.append(0)
            
            axes[0,1].bar(colors, color_performance, color=['lightblue', 'lightcoral'])
            axes[0,1].set_title('V7P3R Win Rate by Color')
            axes[0,1].set_ylabel('Win Rate (%)')
            
            # Game lengths
            valid_lengths = df[df['plycount'] > 0]['plycount']
            if len(valid_lengths) > 0:
                axes[1,0].hist(valid_lengths, bins=20, alpha=0.7, color='lightgreen')
                axes[1,0].set_title('Game Length Distribution')
                axes[1,0].set_xlabel('Plies')
                axes[1,0].set_ylabel('Frequency')
            
            # Timeline of games
            if 'date' in df.columns:
                df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
                valid_dates = df.dropna(subset=['date_parsed'])
                if len(valid_dates) > 0:
                    date_counts = valid_dates['date_parsed'].dt.date.value_counts().sort_index()
                    if len(date_counts) > 1:
                        axes[1,1].plot(date_counts.index, date_counts.values, marker='o')
                        axes[1,1].set_title('Games Over Time')
                        axes[1,1].set_xlabel('Date')
                        axes[1,1].set_ylabel('Number of Games')
                        axes[1,1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.savefig('v7p3r_vs_slowmate_analysis.png', dpi=150, bbox_inches='tight')
            print("Head-to-head visualization saved as 'v7p3r_vs_slowmate_analysis.png'")
            plt.show()
            
        except Exception as e:
            print(f"Error creating visualizations: {e}")
    
    def export_h2h_data(self, df):
        """Export head-to-head data for further analysis."""
        # Detailed game-by-game export
        df.to_csv('v7p3r_vs_slowmate_games.csv', index=False)
        print("\nExported detailed game data to 'v7p3r_vs_slowmate_games.csv'")
        
        # Summary statistics
        summary = {
            'total_games': len(df),
            'v7p3r_wins': 0,
            'slowmate_wins': 0,
            'draws': 0,
            'v7p3r_as_white': len(df[df['v7p3r_color'] == 'white']),
            'v7p3r_as_black': len(df[df['v7p3r_color'] == 'black'])
        }
        
        for _, game in df.iterrows():
            result = game['result']
            v7p3r_color = game['v7p3r_color']
            
            if result == '1/2-1/2':
                summary['draws'] += 1
            elif (result == '1-0' and v7p3r_color == 'white') or (result == '0-1' and v7p3r_color == 'black'):
                summary['v7p3r_wins'] += 1
            elif (result == '0-1' and v7p3r_color == 'white') or (result == '1-0' and v7p3r_color == 'black'):
                summary['slowmate_wins'] += 1
        
        summary_df = pd.DataFrame([summary])
        summary_df.to_csv('v7p3r_vs_slowmate_summary.csv', index=False)
        print("Exported summary statistics to 'v7p3r_vs_slowmate_summary.csv'")

def main():
    print("⚔️  V7P3R vs SlowMate Head-to-Head Analyzer")
    print("==========================================")
    
    analyzer = HeadToHeadAnalyzer()
    
    # Find all head-to-head games
    total_games = analyzer.find_all_h2h_games()
    
    if total_games == 0:
        print("❌ No V7P3R vs SlowMate games found!")
        print("   Check that your PGN files contain games between these engines.")
        return
    
    # Perform comprehensive analysis
    df = analyzer.analyze_overall_performance()
    analyzer.analyze_by_color(df)
    analyzer.analyze_by_time_control(df)
    analyzer.analyze_game_lengths(df)
    analyzer.show_engine_versions()
    
    # Create visualizations and export data
    analyzer.create_h2h_visualizations(df)
    analyzer.export_h2h_data(df)
    
    print("\n✅ Head-to-head analysis complete!")
    print("\nFiles created:")
    print("1. 'v7p3r_vs_slowmate_games.csv' - Detailed game data")
    print("2. 'v7p3r_vs_slowmate_summary.csv' - Summary statistics")
    print("3. 'v7p3r_vs_slowmate_analysis.png' - Visual analysis")

if __name__ == "__main__":
    main()
