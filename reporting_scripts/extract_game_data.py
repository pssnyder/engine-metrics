"""
V7P3R Chess Engine - Game Data ETL Script
Extracts game data from PGN files and version changelog to create conformed dataset
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import csv

# Define base paths
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "raw_data"
GAME_RECORDS_DIR = RAW_DATA_DIR / "game_records" / "Lichess V7P3R Bot"
CHANGELOG_PATH = RAW_DATA_DIR / "v7p3r_docs" / "CHANGELOG.md"
OUTPUT_DIR = BASE_DIR / "reporting_datasets"


class VersionMapper:
    """Maps game dates to engine versions based on CHANGELOG"""
    
    def __init__(self, changelog_path: Path):
        self.version_timeline = self._parse_changelog(changelog_path)
    
    def _parse_changelog(self, path: Path) -> List[Dict]:
        """Parse CHANGELOG.md to extract version deployment timeline"""
        timeline = []
        
        if not path.exists():
            print(f"Warning: CHANGELOG not found at {path}")
            return timeline
        
        content = path.read_text(encoding='utf-8')
        
        # Extract version deployment entries
        # Format: #### **2025-11-30** or ### 2025-12-02
        date_pattern = r'(?:####?\s+\*?\*?|###\s+)(\d{4}-\d{2}-\d{2})'
        version_pattern = r'\*\*Version\*\*:\s+(v[\d.]+)'
        
        lines = content.split('\n')
        current_date = None
        
        for i, line in enumerate(lines):
            date_match = re.search(date_pattern, line)
            if date_match:
                current_date = date_match.group(1)
            
            version_match = re.search(version_pattern, line)
            if version_match and current_date:
                version = version_match.group(1)
                timeline.append({
                    'date': current_date,
                    'version': version
                })
        
        # Sort by date descending (most recent first)
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        print(f"Loaded {len(timeline)} version entries from CHANGELOG")
        return timeline
    
    def get_version_for_date(self, game_date: str) -> str:
        """Map a game date to engine version"""
        # Default to latest known version if before earliest deployment
        if not self.version_timeline:
            return "v17.1"  # Default fallback
        
        for entry in self.version_timeline:
            if game_date >= entry['date']:
                return entry['version']
        
        # If game is older than any recorded version
        return self.version_timeline[-1]['version']


class PGNParser:
    """Parses PGN files to extract game metadata"""
    
    @staticmethod
    def parse_pgn_file(file_path: Path) -> List[Dict]:
        """Parse a PGN file and extract all games"""
        games = []
        
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            return games
        
        content = file_path.read_text(encoding='utf-8')
        
        # Split into individual games
        game_sections = content.split('\n\n[Event ')
        
        for i, section in enumerate(game_sections):
            if i == 0 and not section.startswith('[Event '):
                continue  # Skip any header/preamble
            
            # Add back the [Event tag
            if not section.startswith('[Event '):
                section = '[Event ' + section
            
            game_data = PGNParser._parse_single_game(section)
            if game_data:
                games.append(game_data)
        
        return games
    
    @staticmethod
    def _parse_single_game(pgn_text: str) -> Optional[Dict]:
        """Parse a single game from PGN text"""
        headers = {}
        
        # Extract all PGN headers
        header_pattern = r'\[(\w+)\s+"([^"]*)"\]'
        matches = re.findall(header_pattern, pgn_text)
        
        for key, value in matches:
            headers[key] = value
        
        if not headers:
            return None
        
        # Determine if v7p3r_bot was White or Black
        is_white = headers.get('White', '').lower() == 'v7p3r_bot'
        is_black = headers.get('Black', '').lower() == 'v7p3r_bot'
        
        if not (is_white or is_black):
            return None  # Not a v7p3r_bot game
        
        color = 'white' if is_white else 'black'
        opponent = headers.get('Black' if is_white else 'White', 'Unknown')
        
        # Parse result
        result = headers.get('Result', '*')
        if result == '1-0':
            outcome = 'win' if is_white else 'loss'
        elif result == '0-1':
            outcome = 'loss' if is_white else 'win'
        elif result == '1/2-1/2':
            outcome = 'draw'
        else:
            outcome = 'unknown'
        
        # Parse ELO and rating diff
        v7p3r_elo = int(headers.get('WhiteElo' if is_white else 'BlackElo', 0))
        opponent_elo = int(headers.get('BlackElo' if is_white else 'WhiteElo', 0))
        rating_diff = headers.get('WhiteRatingDiff' if is_white else 'BlackRatingDiff', '0')
        
        # Convert rating diff to int (handle +/- prefix)
        try:
            rating_diff = int(rating_diff.replace('+', ''))
        except ValueError:
            rating_diff = 0
        
        # Extract move count from game text
        moves = re.findall(r'\d+\.', pgn_text)
        move_count = len(moves) if moves else 0
        
        return {
            'game_id': headers.get('GameId', headers.get('Site', '').split('/')[-1]),
            'date': headers.get('UTCDate', headers.get('Date', '')),
            'time': headers.get('UTCTime', ''),
            'event': headers.get('Event', ''),
            'color': color,
            'opponent': opponent,
            'opponent_elo': opponent_elo,
            'v7p3r_elo': v7p3r_elo,
            'result': result,
            'outcome': outcome,
            'rating_diff': rating_diff,
            'time_control': headers.get('TimeControl', ''),
            'eco': headers.get('ECO', ''),
            'opening': headers.get('Opening', ''),
            'termination': headers.get('Termination', ''),
            'move_count': move_count,
            'url': headers.get('Site', '')
        }


def extract_all_games() -> List[Dict]:
    """Extract all V7P3R bot games from PGN files"""
    all_games = []
    
    print(f"Scanning for PGN files in: {GAME_RECORDS_DIR}")
    
    if not GAME_RECORDS_DIR.exists():
        print(f"Error: Game records directory not found: {GAME_RECORDS_DIR}")
        return all_games
    
    # Get all PGN files
    pgn_files = list(GAME_RECORDS_DIR.glob("*.pgn"))
    print(f"Found {len(pgn_files)} PGN files")
    
    for pgn_file in pgn_files:
        print(f"Processing: {pgn_file.name}")
        games = PGNParser.parse_pgn_file(pgn_file)
        all_games.extend(games)
        print(f"  Extracted {len(games)} games")
    
    print(f"\nTotal games extracted: {len(all_games)}")
    return all_games


def enrich_with_versions(games: List[Dict], version_mapper: VersionMapper) -> List[Dict]:
    """Add engine version to each game based on date"""
    enriched_games = []
    
    for game in games:
        game_copy = game.copy()
        game_date = game['date'].replace('.', '-')  # Convert 2026.03.26 to 2026-03-26
        game_copy['engine_version'] = version_mapper.get_version_for_date(game_date)
        enriched_games.append(game_copy)
    
    return enriched_games


def save_dataset(games: List[Dict], output_path: Path):
    """Save games to CSV format"""
    if not games:
        print("No games to save")
        return
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Define field order
    fieldnames = [
        'game_id', 'date', 'time', 'engine_version', 'event', 
        'color', 'outcome', 'result', 'v7p3r_elo', 'opponent', 'opponent_elo',
        'rating_diff', 'time_control', 'eco', 'opening', 'termination',
        'move_count', 'url'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(games)
    
    print(f"\n✓ Dataset saved to: {output_path}")
    print(f"  Total records: {len(games)}")


def main():
    """Main ETL pipeline"""
    print("=" * 60)
    print("V7P3R Chess Engine - Game Data Extraction Pipeline")
    print("=" * 60)
    print()
    
    # Step 1: Load version mapping
    print("Step 1: Loading version timeline from CHANGELOG...")
    version_mapper = VersionMapper(CHANGELOG_PATH)
    print()
    
    # Step 2: Extract games from PGN files
    print("Step 2: Extracting games from PGN files...")
    games = extract_all_games()
    print()
    
    if not games:
        print("No games found. Exiting.")
        return
    
    # Step 3: Enrich with version data
    print("Step 3: Enriching games with engine version data...")
    enriched_games = enrich_with_versions(games, version_mapper)
    print(f"  Enriched {len(enriched_games)} games")
    print()
    
    # Step 4: Save conformed dataset
    output_file = OUTPUT_DIR / f"v7p3r_game_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    print(f"Step 4: Saving conformed dataset...")
    save_dataset(enriched_games, output_file)
    
    # Also save a "latest" version for easy reference
    latest_file = OUTPUT_DIR / "v7p3r_game_data_latest.csv"
    save_dataset(enriched_games, latest_file)
    print(f"  Also saved as: {latest_file}")
    
    print()
    print("=" * 60)
    print("ETL Pipeline Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
