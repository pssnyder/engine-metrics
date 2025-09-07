"""
BayesElo Analysis Script for Chess Engine Tournament Results
Analyzes recent PGN files to calculate accurate ELO ratings using Bayesian inference.
"""

import pandas as pd
import chess.pgn
from pathlib import Path
import subprocess
import tempfile
import re
from datetime import datetime, timedelta
import json

class BayesEloAnalyzer:
    def __init__(self, bayeselo_path="utilities/bayeselo.exe", game_records_path="game_records"):
        self.bayeselo_path = Path(bayeselo_path)
        self.game_records_path = Path(game_records_path)
        self.results = {}
        
        # Engine mapping for consistent naming
        self.engine_mapping = {
            'v7p3r': 'V7P3R',
            'slowmate': 'SlowMate', 
            'cobra': 'C0BR4',
            'c0br4': 'C0BR4',
            'stockfish': 'Stockfish'
        }
    
    def normalize_engine_name(self, name):
        """Normalize engine names for consistent analysis."""
        name_lower = name.lower()
        for key, value in self.engine_mapping.items():
            if key in name_lower:
                return value
        return name
    
    def get_recent_pgn_files(self, days_back=30):
        """Get PGN files from the last N days."""
        print(f"🔍 Finding PGN files from the last {days_back} days...")
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_files = []
        
        battle_dirs = sorted([d for d in self.game_records_path.iterdir() 
                             if d.is_dir() and "Engine Battle" in d.name])
        
        for battle_dir in battle_dirs:
            # Extract date from directory name
            date_str = battle_dir.name.replace("Engine Battle ", "")
            try:
                battle_date = datetime.strptime(date_str, "%Y%m%d")
                if battle_date >= cutoff_date:
                    pgn_files = list(battle_dir.glob("*.pgn"))
                    recent_files.extend(pgn_files)
            except ValueError:
                continue
        
        print(f"📁 Found {len(recent_files)} recent PGN files")
        return recent_files
    
    def extract_games_from_pgn(self, pgn_file):
        """Extract game results from a PGN file."""
        games = []
        
        try:
            with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
                while True:
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        
                        white = game.headers.get('White', '')
                        black = game.headers.get('Black', '')
                        result = game.headers.get('Result', '')
                        
                        # Skip if missing essential data
                        if not white or not black or not result:
                            continue
                        
                        # Normalize engine names
                        white_normalized = self.normalize_engine_name(white)
                        black_normalized = self.normalize_engine_name(black)
                        
                        # Convert result to BayesElo format
                        if result == '1-0':
                            bayeselo_result = '2'  # White wins
                        elif result == '0-1':
                            bayeselo_result = '0'  # Black wins
                        elif result == '1/2-1/2':
                            bayeselo_result = '1'  # Draw
                        else:
                            continue  # Skip games with unclear results
                        
                        games.append({
                            'white': white_normalized,
                            'black': black_normalized,
                            'result': bayeselo_result,
                            'original_white': white,
                            'original_black': black,
                            'original_result': result
                        })
                        
                    except (chess.IllegalMoveError, ValueError, UnicodeDecodeError, EOFError):
                        # Skip corrupted games and continue parsing
                        continue
                    except Exception:
                        # For any other error, skip this game
                        continue
        
        except Exception as e:
            print(f"⚠️  Error reading {pgn_file}: {e}")
        
        return games
    
    def create_bayeselo_script(self, games, output_file="elo_results.txt"):
        """Create a BayesElo script to run the analysis."""
        script_lines = []
        
        # Reset any previous data
        script_lines.append("reset")
        
        # Add all players first
        players = set()
        for game in games:
            players.add(game['white'])
            players.add(game['black'])
        
        for player in sorted(players):
            script_lines.append(f'addplayer "{player}"')
        
        # Add all results
        for game in games:
            script_lines.append(f'addresult "{game["white"]}" "{game["black"]}" {game["result"]}')
        
        # Enter ELO interface and run analysis
        script_lines.extend([
            "elo",
            "mm",  # Use maximum likelihood method
            "exactdist",  # Calculate exact distribution
            f"ratings > {output_file}",  # Save ratings to file
            "p",  # Go back to parent interface
            "x"   # Exit
        ])
        
        return "\n".join(script_lines)
    
    def run_bayeselo_analysis(self, games, analysis_name="recent_analysis"):
        """Run BayesElo analysis on the games."""
        print(f"⚡ Running BayesElo analysis for {analysis_name}...")
        
        # Limit games more aggressively to avoid command length issues
        if len(games) > 200:  # Much smaller limit
            print(f"📊 Limiting to 200 most recent games (from {len(games)} total)")
            games = games[-200:]  # Take most recent 200 games
        
        # Create output file name without spaces to avoid issues
        output_file = f"elo_results_{analysis_name.replace(' ', '_')}.txt"
        
        # Create script content - write to temp file instead of command line
        script_content = self.create_bayeselo_script(games, output_file)
        script_file = f"bayeselo_script_{analysis_name.replace(' ', '_')}.txt"
        
        try:
            # Write script to file
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            # Clean up any existing output files
            cleanup_files = [output_file, f" {output_file}"]  # BayesElo adds leading space
            for file in cleanup_files:
                if Path(file).exists():
                    Path(file).unlink()
            
            # Use file input with full path to avoid directory issues
            bayeselo_full_path = self.game_records_path.parent / "utilities" / "bayeselo.exe"
            shell_command = f'"{bayeselo_full_path}" < "{script_file}"'
            
            result = subprocess.run(
                shell_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.game_records_path.parent,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"⚠️  BayesElo returned error code {result.returncode}")
                if result.stderr:
                    print(f"Stderr: {result.stderr}")
            
            # Check for output file (BayesElo might add leading space)
            possible_files = [output_file, f" {output_file}"]
            actual_output_file = None
            
            for file in possible_files:
                if Path(file).exists():
                    actual_output_file = file
                    break
            
            if actual_output_file:
                results = self.parse_bayeselo_results(actual_output_file)
                # Clean up temp files
                try:
                    Path(actual_output_file).unlink()
                    Path(script_file).unlink()
                except:
                    pass
                return results
            else:
                print("⚠️  No output file generated")
                return None
                
        except subprocess.TimeoutExpired:
            print("⚠️  BayesElo analysis timed out")
            return None
        except Exception as e:
            print(f"⚠️  Error running BayesElo: {e}")
            return None
    
    def parse_bayeselo_results(self, output_file):
        """Parse BayesElo output file to extract ratings."""
        print("📊 Parsing BayesElo results...")
        
        ratings = {}
        
        try:
            with open(output_file, 'r') as f:
                content = f.read()
                
                # Look for rating lines (format varies, but typically includes rank, name, rating, +/-, games)
                lines = content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('Rank'):
                        continue
                    
                    # Try to parse rating line
                    # Typical format: Rank Name Elo +/- #games (score%) (draws%)
                    parts = line.split()
                    
                    if len(parts) >= 4:
                        try:
                            rank = int(parts[0])
                            name = parts[1].strip('"')
                            elo = float(parts[2])
                            error = float(parts[3])
                            
                            ratings[name] = {
                                'rank': rank,
                                'elo': elo,
                                'error': error,
                                'games': int(parts[4]) if len(parts) > 4 else 0
                            }
                        except (ValueError, IndexError):
                            continue
                
        except Exception as e:
            print(f"⚠️  Error parsing results: {e}")
        
        return ratings
    
    def analyze_time_periods(self, days_list=[7, 14, 30]):
        """Analyze multiple time periods to show ELO evolution."""
        print("📈 Analyzing ELO evolution over different time periods...")
        
        all_results = {}
        
        for days in days_list:
            print(f"\n🗓️  Analyzing last {days} days...")
            
            # Get recent files for this period
            recent_files = self.get_recent_pgn_files(days_back=days)
            
            if not recent_files:
                print(f"   No files found for last {days} days")
                continue
            
            # Extract all games
            all_games = []
            for pgn_file in recent_files:
                games = self.extract_games_from_pgn(pgn_file)
                all_games.extend(games)
            
            if not all_games:
                print(f"   No valid games found for last {days} days")
                continue
            
            print(f"   📊 Found {len(all_games)} games")
            
            # Run BayesElo analysis
            ratings = self.run_bayeselo_analysis(all_games, f"last_{days}_days")
            
            if ratings:
                all_results[f"last_{days}_days"] = {
                    'ratings': ratings,
                    'games_count': len(all_games),
                    'period': f"Last {days} days"
                }
                print(f"   ✅ Analysis complete: {len(ratings)} engines rated")
            else:
                print(f"   ❌ Analysis failed for last {days} days")
        
        return all_results
    
    def create_comparison_report(self, all_results):
        """Create a comprehensive comparison report."""
        print("📝 Creating comparison report...")
        
        report = f"""# BayesElo Analysis Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This report shows ELO ratings calculated using BayesElo (Bayesian inference) for different time periods.
BayesElo provides more accurate ratings than simple performance calculations, especially with limited games.

"""
        
        # Create comparison table
        all_engines = set()
        for period_data in all_results.values():
            all_engines.update(period_data['ratings'].keys())
        
        if all_engines:
            report += "## ELO Ratings Comparison\n\n"
            report += "| Engine | "
            
            periods = list(all_results.keys())
            for period in periods:
                report += f"{all_results[period]['period']} | "
            report += "\n"
            
            report += "|--------|"
            for _ in periods:
                report += "--------|"
            report += "\n"
            
            for engine in sorted(all_engines):
                report += f"| **{engine}** | "
                
                for period in periods:
                    if engine in all_results[period]['ratings']:
                        rating_data = all_results[period]['ratings'][engine]
                        elo = rating_data['elo']
                        error = rating_data['error']
                        games = rating_data['games']
                        report += f"{elo:.0f} ± {error:.0f} ({games} games) | "
                    else:
                        report += "- | "
                
                report += "\n"
            
            # Add detailed breakdown for each period
            report += "\n## Detailed Analysis by Period\n\n"
            
            for period, data in all_results.items():
                report += f"### {data['period']}\n"
                report += f"- **Total Games**: {data['games_count']}\n"
                report += f"- **Engines Analyzed**: {len(data['ratings'])}\n\n"
                
                # Sort engines by ELO
                sorted_engines = sorted(data['ratings'].items(), 
                                      key=lambda x: x[1]['elo'], reverse=True)
                
                report += "| Rank | Engine | ELO | Error | Games |\n"
                report += "|------|--------|-----|-------|-------|\n"
                
                for engine, rating_data in sorted_engines:
                    report += f"| {rating_data['rank']} | {engine} | {rating_data['elo']:.0f} | ±{rating_data['error']:.0f} | {rating_data['games']} |\n"
                
                report += "\n"
        
        # Add methodology section
        report += """## Methodology

### BayesElo vs Simple ELO Calculation
- **BayesElo**: Uses Bayesian inference to estimate rating distributions
- **Advantages**: 
  - More accurate with limited games
  - Provides confidence intervals (error margins)
  - Handles uneven game distributions better
  - Less sensitive to outlier results

### Rating Interpretation
- **ELO ± Error**: The rating with confidence interval
- **Games**: Number of games used for calculation
- **Rank**: Position in the rating list

### Data Sources
- Recent tournament PGN files from game_records directory
- Normalized engine names for consistency
- Only games with clear results (1-0, 0-1, 1/2-1/2)

---

*Analysis performed using BayesElo v0056 by Remi Coulom*
"""
        
        return report
    
    def save_results(self, all_results, report):
        """Save results to files."""
        print("💾 Saving results...")
        
        # Save JSON data
        json_data = {}
        for period, data in all_results.items():
            json_data[period] = {
                'period_name': data['period'],
                'games_count': data['games_count'],
                'ratings': data['ratings']
            }
        
        with open('bayeselo_analysis_results.json', 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Save markdown report
        with open('bayeselo_analysis_report.md', 'w') as f:
            f.write(report)
        
        # Save CSV for easy Excel import
        csv_data = []
        for period, data in all_results.items():
            for engine, rating_data in data['ratings'].items():
                csv_data.append({
                    'period': data['period'],
                    'engine': engine,
                    'elo': rating_data['elo'],
                    'error': rating_data['error'],
                    'games': rating_data['games'],
                    'rank': rating_data['rank']
                })
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv('bayeselo_ratings.csv', index=False)
        
        print("✅ Results saved:")
        print("   📊 bayeselo_analysis_results.json - Raw data")
        print("   📝 bayeselo_analysis_report.md - Detailed report")
        print("   📋 bayeselo_ratings.csv - CSV for Excel")

def main():
    print("🔍 BayesElo Analysis for Chess Engine Tournaments")
    print("=" * 55)
    
    analyzer = BayesEloAnalyzer()
    
    # Check if BayesElo exists
    if not analyzer.bayeselo_path.exists():
        print(f"❌ BayesElo not found at {analyzer.bayeselo_path}")
        print("   Please ensure bayeselo.exe is in the utilities directory")
        return
    
    print(f"✅ BayesElo found at {analyzer.bayeselo_path}")
    
    # Analyze different time periods
    time_periods = [7, 14, 30]  # Last 7, 14, and 30 days
    
    try:
        all_results = analyzer.analyze_time_periods(time_periods)
        
        if not all_results:
            print("❌ No analysis results generated")
            return
        
        # Create and save report
        report = analyzer.create_comparison_report(all_results)
        analyzer.save_results(all_results, report)
        
        print("\n🎉 BayesElo analysis complete!")
        print("\nKey findings:")
        
        # Show latest period summary
        latest_period = max(all_results.keys(), key=lambda k: int(k.split('_')[1]))
        latest_data = all_results[latest_period]
        
        print(f"\n📊 {latest_data['period']} Summary:")
        sorted_engines = sorted(latest_data['ratings'].items(), 
                              key=lambda x: x[1]['elo'], reverse=True)
        
        for engine, rating_data in sorted_engines[:5]:  # Top 5
            elo = rating_data['elo']
            error = rating_data['error']
            games = rating_data['games']
            print(f"   {engine}: {elo:.0f} ± {error:.0f} ELO ({games} games)")
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    main()
