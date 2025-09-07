#!/usr/bin/env python3
"""
Manual BayesElo test - create script file and run manually
"""

import os
import chess.pgn
from pathlib import Path
from datetime import datetime, timedelta

def create_manual_test():
    """Create BayesElo script for manual testing."""
    print("🧪 Creating manual BayesElo test script...")
    
    os.chdir(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
    
    # Get recent games
    game_records = Path("game_records")
    recent_files = []
    
    cutoff_date = datetime.now() - timedelta(days=3)  # Just last 3 days
    
    for battle_dir in sorted(game_records.iterdir(), reverse=True):
        if battle_dir.is_dir() and "Engine Battle" in battle_dir.name:
            date_str = battle_dir.name.replace("Engine Battle ", "")
            try:
                battle_date = datetime.strptime(date_str, "%Y%m%d")
                if battle_date >= cutoff_date:
                    pgn_files = list(battle_dir.glob("*.pgn"))
                    recent_files.extend(pgn_files)
            except ValueError:
                continue
    
    print(f"📁 Found {len(recent_files)} recent PGN files")
    
    # Extract games
    games = []
    engines = set()
    
    for pgn_file in recent_files[:3]:  # Just first 3 files
        print(f"📄 Processing: {pgn_file}")
        try:
            with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
                game_count = 0
                while game_count < 50:  # Max 50 games per file
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        
                        white = game.headers.get('White', '').strip()
                        black = game.headers.get('Black', '').strip()
                        result = game.headers.get('Result', '')
                        
                        if not white or not black or not result:
                            continue
                        
                        # Clean engine names
                        white = white.replace('_', ' ').replace('.', ' ')
                        black = black.replace('_', ' ').replace('.', ' ')
                        
                        engines.add(white)
                        engines.add(black)
                        
                        # Convert result
                        if result == '1-0':
                            bayeselo_result = '2'
                        elif result == '0-1':
                            bayeselo_result = '0'
                        elif result == '1/2-1/2':
                            bayeselo_result = '1'
                        else:
                            continue
                        
                        games.append((white, black, bayeselo_result))
                        game_count += 1
                        
                    except Exception as e:
                        # Skip problematic games
                        continue
                        
        except Exception as e:
            print(f"❌ Error with {pgn_file}: {e}")
            continue
    
    print(f"📊 Extracted {len(games)} games with {len(engines)} engines")
    print(f"🏁 Engines: {', '.join(sorted(engines))}")
    
    # Create BayesElo script
    script_lines = ["reset"]
    
    # Add players
    for engine in sorted(engines):
        script_lines.append(f'addplayer "{engine}"')
    
    # Add results
    for white, black, result in games:
        script_lines.append(f'addresult "{white}" "{black}" {result}')
    
    # Add analysis commands
    script_lines.extend([
        "elo",
        "mm", 
        "exactdist",
        "ratings > manual_test_results.txt",
        "x"
    ])
    
    script_content = "\n".join(script_lines)
    
    # Save script
    with open("manual_bayeselo_script.txt", 'w') as f:
        f.write(script_content)
    
    print(f"📝 Script saved to: manual_bayeselo_script.txt")
    print(f"📊 Script has {len(script_lines)} lines")
    print("\n🚀 To run manually:")
    print("utilities\\bayeselo.exe < manual_bayeselo_script.txt")
    print("\n📋 Or run the commands:")
    print("cd \"s:\\Maker Stuff\\Programming\\Chess Engines\\Chess Engine Playground\\engine-metrics\"")
    print("utilities\\bayeselo.exe < manual_bayeselo_script.txt")

if __name__ == "__main__":
    create_manual_test()
