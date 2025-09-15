#!/usr/bin/env python3
"""
Show what data BayesElo actually uses from PGNs
"""

import chess.pgn
from pathlib import Path

def analyze_pgn_data_usage():
    """Show what data we extract vs what we ignore."""
    
    # Find a recent PGN file
    game_records = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\game_records")
    
    # Get the most recent battle directory
    battle_dirs = sorted([d for d in game_records.iterdir() 
                         if d.is_dir() and "Engine Battle" in d.name])
    
    if not battle_dirs:
        print("No battle directories found")
        return
    
    recent_dir = battle_dirs[-1]
    pgn_files = list(recent_dir.glob("*.pgn"))
    
    if not pgn_files:
        print("No PGN files found")
        return
    
    sample_file = pgn_files[0]
    print(f"📁 Analyzing: {sample_file}")
    print("=" * 60)
    
    games_analyzed = 0
    
    with open(sample_file, 'r', encoding='utf-8', errors='ignore') as f:
        while games_analyzed < 3:  # Just analyze first 3 games
            try:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                
                print(f"\n🎮 Game {games_analyzed + 1}:")
                print("📊 ALL PGN HEADERS:")
                for key, value in game.headers.items():
                    marker = "✅ USED" if key in ['White', 'Black', 'Result'] else "❌ IGNORED"
                    print(f"  {marker} {key}: {value}")
                
                print("\n🎯 WHAT BAYESELO ACTUALLY USES:")
                white = game.headers.get('White', '')
                black = game.headers.get('Black', '')
                result = game.headers.get('Result', '')
                
                # Convert to BayesElo format
                if result == '1-0':
                    bayeselo_result = '2 (White wins)'
                elif result == '0-1':
                    bayeselo_result = '0 (Black wins)'
                elif result == '1/2-1/2':
                    bayeselo_result = '1 (Draw)'
                else:
                    bayeselo_result = 'Invalid'
                
                print(f"  addresult \"{white}\" \"{black}\" {bayeselo_result}")
                
                games_analyzed += 1
                print("-" * 40)
                
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    analyze_pgn_data_usage()
