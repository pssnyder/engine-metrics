"""
V7P3R Chess Engine - Enhanced Move-Level Data Extraction
Parses PGN move notation to extract castling, material, time, and positional data
"""

import re
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Define base paths
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "raw_data"
GAME_RECORDS_DIR = RAW_DATA_DIR / "game_records" / "Lichess V7P3R Bot"
OUTPUT_DIR = BASE_DIR / "reporting_datasets"

# Piece values for material calculation
PIECE_VALUES = {
    'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0,
    'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0
}

# ECO to opening family mapping (major groups)
ECO_FAMILIES = {
    'A': {'00-03': 'Irregular Openings', '04-09': 'Reti Opening', '10-39': 'English Opening',
          '40-44': 'Queen\'s Pawn', '45-49': 'Trompowsky Attack', '50-79': 'Indian Defenses',
          '80-99': 'Dutch Defense'},
    'B': {'00-19': 'Uncommon King Pawn', '20-99': 'Sicilian Defense'},
    'C': {'00-19': 'French Defense', '20-29': 'French Defense', '30-39': 'French Defense',
          '40-49': 'King\'s Pawn Game', '50-59': 'Italian Game', '60-99': 'Ruy Lopez'},
    'D': {'00-05': 'Queen\'s Pawn Game', '06-69': 'Queen\'s Gambit', '70-99': 'Grunfeld Defense'},
    'E': {'00-09': 'Catalan Opening', '10-19': 'Slav Defense', '20-59': 'Nimzo-Indian Defense',
          '60-99': 'King\'s Indian Defense'}
}

def get_opening_family(eco: str) -> str:
    """Map ECO code to opening family"""
    if not eco or len(eco) < 3:
        return "Unknown"
    
    letter = eco[0].upper()
    try:
        number = int(eco[1:])
    except (ValueError, IndexError):
        return "Unknown"
    
    if letter not in ECO_FAMILIES:
        return "Unknown"
    
    for range_key, family in ECO_FAMILIES[letter].items():
        if '-' in range_key:
            start, end = map(int, range_key.split('-'))
            if start <= number <= end:
                return family
    
    return f"{letter}{number:02d} Opening"


class MoveParser:
    """Parse PGN move notation and extract move-level data"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state"""
        self.white_material = 39  # Starting material (8p + 2n + 2b + 2r + q)
        self.black_material = 39
        self.white_queens = 1
        self.black_queens = 1
        self.white_castled = None  # None, 'kingside', 'queenside'
        self.black_castled = None
        self.queen_traded_move = None
    
    def parse_move(self, move_text: str) -> Dict:
        """Parse a single move in SAN notation"""
        move_data = {
            'san': move_text,
            'piece': None,
            'is_capture': 'x' in move_text,
            'is_check': '+' in move_text,
            'is_checkmate': '#' in move_text,
            'is_castle': False,
            'castle_side': None,
            'promotion': None
        }
        
        # Check for castling
        if 'O-O-O' in move_text or '0-0-0' in move_text:
            move_data['is_castle'] = True
            move_data['castle_side'] = 'queenside'
            move_data['piece'] = 'K'
        elif 'O-O' in move_text or '0-0' in move_text:
            move_data['is_castle'] = True
            move_data['castle_side'] = 'kingside'
            move_data['piece'] = 'K'
        else:
            # Extract piece (first character if uppercase, else pawn)
            clean_move = move_text.replace('+', '').replace('#', '').replace('x', '')
            if clean_move and clean_move[0].isupper():
                move_data['piece'] = clean_move[0]
            else:
                move_data['piece'] = 'P'  # Pawn
            
            # Check for promotion
            if '=' in move_text:
                move_data['promotion'] = move_text.split('=')[1][0]
        
        return move_data
    
    def update_material(self, move_data: Dict, color: str):
        """Update material count based on captures"""
        if not move_data['is_capture']:
            return
        
        # Rough estimate: assume average piece captured is 3 points
        # This is simplified - for perfect accuracy we'd need board state
        captured_value = 3  # Average of knight/bishop
        
        if color == 'white':
            self.black_material -= captured_value
        else:
            self.white_material -= captured_value
    
    def update_queens(self, move_data: Dict, color: str):
        """Track queen captures/trades"""
        if move_data['piece'] == 'Q' and move_data['is_capture']:
            # Queen was captured or traded
            if color == 'white':
                self.black_queens = max(0, self.black_queens - 1)
            else:
                self.white_queens = max(0, self.white_queens - 1)
    
    def update_castling(self, move_data: Dict, color: str, move_number: int):
        """Track castling"""
        if move_data['is_castle']:
            if color == 'white':
                self.white_castled = move_data['castle_side']
            else:
                self.black_castled = move_data['castle_side']


class EnhancedPGNParser:
    """Parse PGN files with move-level analysis"""
    
    @staticmethod
    def parse_game_moves(pgn_text: str) -> Tuple[List[Dict], Dict]:
        """Parse game and return moves list + game summary data"""
        # Extract headers
        headers = {}
        header_pattern = r'\[(\w+)\s+"([^"]*)"\]'
        matches = re.findall(header_pattern, pgn_text)
        for key, value in matches:
            headers[key] = value
        
        # Check if v7p3r_bot game
        is_white = headers.get('White', '').lower() == 'v7p3r_bot'
        is_black = headers.get('Black', '').lower() == 'v7p3r_bot'
        
        if not (is_white or is_black):
            return [], {}
        
        v7p3r_color = 'white' if is_white else 'black'
        
        # Extract move text (everything after headers)
        move_section = re.split(r'\n\n', pgn_text, maxsplit=1)
        if len(move_section) < 2:
            return [], {}
        
        move_text = move_section[1]
        
        # Parse moves with clock times
        # Pattern: 1. e4 { [%clk 0:05:00] } or just 1. e4
        move_pattern = r'(\d+)\.\s+([^\s{]+)\s*(?:\{\s*\[%clk\s+([^\]]+)\]\s*\})?\s*(?:\.\.\.\s+)?([^\s{]+)?\s*(?:\{\s*\[%clk\s+([^\]]+)\]\s*\})?'
        
        moves = []
        parser = MoveParser()
        
        for match in re.finditer(move_pattern, move_text):
            move_num = int(match.group(1))
            white_move = match.group(2)
            white_clock = match.group(3)
            black_move = match.group(4)
            black_clock = match.group(5)
            
            # Parse White's move
            if white_move:
                white_data = parser.parse_move(white_move)
                parser.update_material(white_data, 'white')
                parser.update_queens(white_data, 'white')
                parser.update_castling(white_data, 'white', move_num)
                
                moves.append({
                    'move_number': move_num,
                    'color': 'white',
                    'san': white_move,
                    'piece': white_data['piece'],
                    'is_capture': white_data['is_capture'],
                    'is_check': white_data['is_check'],
                    'is_castle': white_data['is_castle'],
                    'castle_side': white_data['castle_side'],
                    'clock': white_clock,
                    'white_material': parser.white_material,
                    'black_material': parser.black_material,
                    'material_balance': parser.white_material - parser.black_material
                })
            
            # Parse Black's move
            if black_move and black_move not in ['1-0', '0-1', '1/2-1/2', '*']:
                black_data = parser.parse_move(black_move)
                parser.update_material(black_data, 'black')
                parser.update_queens(black_data, 'black')
                parser.update_castling(black_data, 'black', move_num)
                
                moves.append({
                    'move_number': move_num,
                    'color': 'black',
                    'san': black_move,
                    'piece': black_data['piece'],
                    'is_capture': black_data['is_capture'],
                    'is_check': black_data['is_check'],
                    'is_castle': black_data['is_castle'],
                    'castle_side': black_data['castle_side'],
                    'clock': black_clock,
                    'white_material': parser.white_material,
                    'black_material': parser.black_material,
                    'material_balance': parser.white_material - parser.black_material
                })
        
        # Check for queen trade
        queen_traded_move = None
        if parser.white_queens == 0 and parser.black_queens == 0:
            # Both queens off board - find when it happened
            for move in moves:
                if move['piece'] == 'Q' and move['is_capture']:
                    queen_traded_move = move['move_number']
                    break
        
        # Determine game phase for each move
        total_moves = len(moves)
        for i, move in enumerate(moves):
            # Phase based on move number and material
            move_num = move['move_number']
            total_material = move['white_material'] + move['black_material']
            
            if move_num <= 15:
                phase = 'opening'
            elif total_material > 40 or move_num <= 40:
                phase = 'middlegame'
            else:
                phase = 'endgame'
            
            move['game_phase'] = phase
        
        # Build game summary
        summary = {
            'game_id': headers.get('GameId', headers.get('Site', '').split('/')[-1]),
            'v7p3r_color': v7p3r_color,
            'v7p3r_castled': parser.white_castled if is_white else parser.black_castled,
            'opponent_castled': parser.black_castled if is_white else parser.white_castled,
            'queen_traded': queen_traded_move is not None,
            'queen_traded_move': queen_traded_move,
            'total_moves': len(moves),
            'opening_family': get_opening_family(headers.get('ECO', ''))
        }
        
        return moves, summary


def extract_enhanced_data():
    """Main extraction function"""
    print("=" * 80)
    print("V7P3R Enhanced Move-Level Data Extraction")
    print("=" * 80)
    print()
    
    if not GAME_RECORDS_DIR.exists():
        print(f"Error: Game records directory not found: {GAME_RECORDS_DIR}")
        return
    
    pgn_files = list(GAME_RECORDS_DIR.glob("*.pgn"))
    print(f"Found {len(pgn_files)} PGN files\n")
    
    all_moves = []
    all_summaries = []
    games_processed = 0
    
    for pgn_file in pgn_files:
        print(f"Processing: {pgn_file.name}")
        content = pgn_file.read_text(encoding='utf-8')
        
        # Split into individual games
        game_sections = content.split('\n\n[Event ')
        
        for i, section in enumerate(game_sections):
            if i == 0 and not section.startswith('[Event '):
                continue
            
            if not section.startswith('[Event '):
                section = '[Event ' + section
            
            moves, summary = EnhancedPGNParser.parse_game_moves(section)
            
            if moves and summary:
                game_id = summary['game_id']
                
                # Add game_id to each move
                for move in moves:
                    move['game_id'] = game_id
                
                all_moves.extend(moves)
                all_summaries.append(summary)
                games_processed += 1
        
        print(f"  Processed {games_processed} games so far...")
    
    print(f"\nTotal games processed: {games_processed}")
    print(f"Total moves extracted: {len(all_moves)}")
    
    # Save moves dataset
    if all_moves:
        moves_file = OUTPUT_DIR / "v7p3r_moves_latest.csv"
        moves_file.parent.mkdir(parents=True, exist_ok=True)
        
        move_fields = ['game_id', 'move_number', 'color', 'san', 'piece', 'is_capture',
                      'is_check', 'is_castle', 'castle_side', 'clock', 'white_material',
                      'black_material', 'material_balance', 'game_phase']
        
        with open(moves_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=move_fields)
            writer.writeheader()
            writer.writerows(all_moves)
        
        print(f"\n✓ Moves dataset saved: {moves_file}")
    
    # Save enhanced game summaries
    if all_summaries:
        summary_file = OUTPUT_DIR / "v7p3r_game_summary_enhanced_latest.csv"
        
        summary_fields = ['game_id', 'v7p3r_color', 'v7p3r_castled', 'opponent_castled',
                         'queen_traded', 'queen_traded_move', 'total_moves', 'opening_family']
        
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerows(all_summaries)
        
        print(f"✓ Game summaries saved: {summary_file}")
    
    print()
    print("=" * 80)
    print("Enhanced Data Extraction Complete!")
    print("=" * 80)


if __name__ == "__main__":
    extract_enhanced_data()
