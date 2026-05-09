# Enhanced PGN to CSV Parser
# Extracts game metadata from PGN files without validating moves
# Features: Progress bar, error handling, fast parsing, summary statistics
import os
import csv
import re
from pathlib import Path
from tqdm import tqdm
from collections import Counter

def count_pgn_files(directory: str) -> int:
    """Count total PGN files for progress bar."""
    return sum(1 for _ in Path(directory).rglob('*.pgn'))

def extract_headers_fast(pgn_text: str) -> dict:
    """
    Extract PGN headers without validating moves.
    Fast regex-based extraction that skips move validation entirely.
    """
    headers = {}
    # Match PGN headers: [Key "Value"]
    header_pattern = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
    
    for match in header_pattern.finditer(pgn_text):
        key, value = match.groups()
        headers[key] = value
    
    return headers

def parse_pgn_file_fast(filepath: str) -> list[dict]:
    """
    Parse a single PGN file and extract all game headers.
    Returns list of game header dictionaries.
    """
    games = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split on empty lines between games (PGN standard)
        # Games are separated by blank lines
        game_blocks = re.split(r'\n\s*\n\[', content)
        
        for i, block in enumerate(game_blocks):
            if not block.strip():
                continue
            
            # Add back the [ if it was stripped during split
            if i > 0 and not block.startswith('['):
                block = '[' + block
            
            headers = extract_headers_fast(block)
            
            # Only add if we got meaningful headers
            if headers and 'White' in headers and 'Black' in headers:
                games.append(headers)
    
    except Exception as e:
        print(f"\n⚠️  Error reading {filepath}: {e}")
    
    return games

def parse_pgn_files_to_csv(pgn_directory: str, output_csv: str):
    """
    Parse all PGN files in directory tree and output to CSV.
    Shows progress bar and summary statistics.
    """
    fieldnames = ['Event', 'Site', 'Date', 'Round', 'White', 'Black', 'Result', 
                  'BlackElo', 'ECO', 'Opening', 'Time', 'Variation', 
                  'WhiteElo', 'TimeControl', 'Termination', 'PlyCount',
                  'WhiteType', 'BlackType', 'SourceFile']
    
    # Count files for progress bar
    print("🔍 Counting PGN files...")
    total_files = count_pgn_files(pgn_directory)
    print(f"📂 Found {total_files:,} PGN files to process\n")
    
    games_written = 0
    files_processed = 0
    files_with_errors = 0
    result_stats = Counter()
    
    with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process files with progress bar
        pgn_files = list(Path(pgn_directory).rglob('*.pgn'))
        
        for pgn_path in tqdm(pgn_files, desc="Processing PGN files", unit="file"):
            files_processed += 1
            games = parse_pgn_file_fast(str(pgn_path))
            
            if not games:
                files_with_errors += 1
                continue
            
            for headers in games:
                row = {
                    'Event': headers.get('Event', ''),
                    'Site': headers.get('Site', ''),
                    'Date': headers.get('Date', ''),
                    'Round': headers.get('Round', ''),
                    'White': headers.get('White', ''),
                    'Black': headers.get('Black', ''),
                    'Result': headers.get('Result', ''),
                    'BlackElo': headers.get('BlackElo', ''),
                    'ECO': headers.get('ECO', ''),
                    'Opening': headers.get('Opening', ''),
                    'Time': headers.get('Time', ''),
                    'Variation': headers.get('Variation', ''),
                    'WhiteElo': headers.get('WhiteElo', ''),
                    'TimeControl': headers.get('TimeControl', ''),
                    'Termination': headers.get('Termination', ''),
                    'PlyCount': headers.get('PlyCount', ''),
                    'WhiteType': headers.get('WhiteType', ''),
                    'BlackType': headers.get('BlackType', ''),
                    'SourceFile': str(pgn_path.relative_to(pgn_directory))
                }
                
                writer.writerow(row)
                games_written += 1
                
                # Track result statistics
                result = headers.get('Result', 'Unknown')
                result_stats[result] += 1
    
    # Print summary
    print(f"\n✅ Processing complete!")
    print(f"{'='*60}")
    print(f"📊 Summary Statistics:")
    print(f"{'='*60}")
    print(f"  Files processed:     {files_processed:,}")
    print(f"  Files with errors:   {files_with_errors:,}")
    print(f"  Games extracted:     {games_written:,}")
    print(f"\n📈 Game Results:")
    print(f"{'='*60}")
    for result, count in result_stats.most_common():
        percentage = (count / games_written * 100) if games_written > 0 else 0
        print(f"  {result:20} {count:8,} ({percentage:5.1f}%)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Configuration
    pgn_directory = r'E:\Programming Stuff\Chess Engines\Chess Engine Playground\engine-metrics\raw_data\game_records'
    output_csv = r'games_20260426.csv'
    
    print(f"🚀 Starting PGN to CSV conversion")
    print(f"📁 Source: {pgn_directory}")
    print(f"💾 Output: {output_csv}\n")
    
    parse_pgn_files_to_csv(pgn_directory, output_csv)
    
    print(f"✨ CSV file saved to: {output_csv}")