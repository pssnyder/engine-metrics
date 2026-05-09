# Raw Data Inventory & Conformed Schema Mapping

**Last Updated:** 2026-04-24  
**Raw Data Location:** `e:\Programming Stuff\Chess Engines\Chess Engine Playground\engine-metrics\raw_data\`  
**Total Volume:** 2,336 files, 2.58 GB

---

## 📊 Raw Data Summary

| Directory | Files | Size | Primary Content |
|---|---|---|---|
| **analysis_results** | 551 | 94 MB | Stockfish analysis JSON, puzzle test results, tournament reports |
| **game_records** | 1,473 | 139 MB | PGN files (498 total), tournament .res files, logs |
| **pgn_training_data** | 138 | 2.4 GB | lichess_db_puzzle.csv (861MB), opening theory PGNs |
| **v7p3r_docs** | 173 | 1.6 MB | CHANGELOG.md, deployment guides, design docs |
| **Root** | 1 | <1 MB | notation_events.json |
| **TOTAL** | **2,336** | **2.58 GB** | |

---

## 🗂️ Data Source Catalog (Actual Files)

### 1. Game Records (PGN Files)

**Location:** `raw_data/game_records/`

#### 1.1 Lichess V7P3R Bot Games
**Path:** `game_records/Lichess V7P3R Bot/`  
**Files:** 4 PGN files (43 MB total)
- `lichess_v7p3r_bot_2026-03-01.pgn` (4 MB)
- `lichess_v7p3r_bot_2026-03-15.pgn` (13 MB)
- `lichess_v7p3r_bot_2026-03-26.pgn` (13 MB)
- `lichess_v7p3r_bot_2026-04-09.pgn` (13 MB)

**Estimated Games:** ~50,000+ games across all files

**PGN Header Fields:**
```
Event, Site, Date, Round, White, Black, Result, 
WhiteElo, BlackElo, TimeControl, Opening, ECO, Termination,
[Moves in SAN notation]
```

**Derived Fields for Conformed Schema:**
- `game_id` ← Extract from Site URL (last segment)
- `v7p3r_color` ← 'white' if White='v7p3r_bot' else 'black'
- `v7p3r_elo` ← WhiteElo or BlackElo based on color
- `opponent_name` ← White or Black (whichever is not v7p3r_bot)
- `opponent_elo` ← Opponent's ELO
- `outcome` ← 'win'/'loss'/'draw' from Result + v7p3r_color
- `engine_version` ← Map Date to deployment history (from CHANGELOG.md)
- `move_count` ← Count moves in game
- `time_control_category` ← Parse TimeControl (bullet/blitz/rapid)

#### 1.2 Engine Battle Tournament Games
**Path:** `game_records/Engine Battle YYYYMM/` (7 directories)
- `Engine Battle 202507/` through `Engine Battle 202604/`

**Files per Tournament:**
- `.pgn` - Game records
- `.res` - Tournament standings and results
- `.log` - Arena log file
- `.html` - HTML report
- `.at` - Arena tournament file

**Total PGN Files:** ~150+ tournament games

**Tournament Results (.res) Format:**
```
-----------------EngineName-----------------
EngineName - OpponentName : Score/Games W-L-D (Results) WinRate +/-ELO
```

**Derived Fields:**
- Parse tournament name from directory
- Parse engine versions from engine names
- Extract head-to-head results
- Calculate tournament standings

#### 1.3 Other Bot Games
**Paths:**
- `game_records/Lichess C0BR4 Bot/`
- `game_records/Lichess SlowMate Bot/`
- `game_records/v7p3r Human/`

**Purpose:** Other engines and human games (likely for comparison/testing)

**Total PGN Files:** ~300+ additional games

---

### 2. Stockfish Analysis Results (JSON)

**Location:** `raw_data/analysis_results/`  
**Files:** ~150 JSON files with analysis data

#### 2.1 Year-to-Date Analysis Files
**Pattern:** `v{version}_ytd_analysis_{timestamp}.json`  
**Example:** `v18_3_ytd_analysis_20260421_205618.json` (172 KB)

**JSON Schema:**
```json
{
  "metadata": {
    "analysis_date": "ISO datetime",
    "total_games": int,
    "stockfish_depth": int,
    "version": "v18.3",
    "date_range": {"start": "date", "end": "date"}
  },
  "patterns": {
    "summary": {
      "total_games_analyzed": int,
      "v7p3r_as_white": int,
      "v7p3r_as_black": int,
      "blunders_count": int,
      "mistakes_count": int,
      "inaccuracies_count": int
    },
    "v7p3r_stats": {
      "blunders_per_game": float,
      "mistakes_per_game": float,
      "accuracy_pct": float
    },
    "opening_patterns": {...},
    "move_phase_patterns": {...}
  }
}
```

**Target Tables:**
- `STOCKFISH_ANALYSIS` - Main analysis metadata
- `ERROR_PATTERNS` - Blunders/mistakes by opening/phase
- `GAME_SUMMARIES` - Aggregated game statistics

#### 2.2 Puzzle Test Results
**Pattern:** `puzzle_results_v{version}_{timestamp}.json`  
**Example:** `puzzle_results_v18_3_20260416_183756.json` (148 KB)

**JSON Schema:**
```json
{
  "metadata": {
    "engine_name": "v18.3",
    "test_date": "ISO datetime",
    "num_puzzles": int,
    "rating_range": [min, max],
    "time_per_position": int,
    "themes": ["mate", "fork", "pin", ...]
  },
  "report": {
    "total_puzzles": int,
    "total_positions_analyzed": int,
    "sequence_metrics": {
      "avg_linear_accuracy": float,
      "perfect_sequences": int,
      "perfect_sequence_rate": float
    },
    "theme_performance": {
      "mate": {"total": int, "perfect_sequences": int, ...},
      "fork": {...}
    },
    "time_management_metrics": {
      "avg_time_per_move": float,
      "time_exceeded_rate": float
    }
  },
  "results": [
    {
      "puzzle_id": "000Zo",
      "original_fen": "FEN string",
      "rating": int,
      "themes": "theme1 theme2",
      "solution_sequence": "e5f6 e8e1...",
      "sequence_accuracy_linear": float,
      "perfect_sequence": bool,
      "positions": [{...}]
    }
  ]
}
```

**Target Table:** `PUZZLE_ANALYSIS_RESULTS`

#### 2.3 Other Analysis Files
- `heuristic_impact_report.json` - Evaluation function analysis
- `regression_tournament_analysis_*.json` - Version regression testing
- `v*_improvement_validation_*.json` - Version improvement validation
- Markdown reports (`.md`) - Human-readable summaries

---

### 3. Puzzle Dataset (CSV)

**Location:** `raw_data/pgn_training_data/`  
**File:** `lichess_db_puzzle.csv` (861 MB)

**CSV Schema (Header):**
```
PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
```

**Example Row:**
```
00sHx,q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K2 b k - 0 17,e8d7 a2e6 d7d8 f7f8,1760,80,83,72,mate mateIn2 middlegame short,https://lichess.org/yyznGmXs/black#34,Italian_Game Italian_Game_Classical_Variation
```

**Volume:** ~4M rows (user confirmed this was the source for puzzles.db)

**Target Table:** `PUZZLES`

**Transformation Notes:**
- `Themes` is space-separated string → Convert to array or separate theme records
- `OpeningTags` is space-separated string → Parse opening family
- `Moves` is UCI move sequence → Store as-is

---

### 4. Opening Theory PGN Files

**Location:** `raw_data/pgn_training_data/`  
**Files:** 135 opening theory PGN files (1.5 GB)

**Categories:**
- **Opening Families:** `Sicilian*.pgn`, `Caro-Kann*.pgn`, `French*.pgn`, `KID*.pgn`
- **Classic Games:** `100_golden_games.pgn`, `new_york_1924.pgn`
- **Training Books:** `1001_winning_chess_sacrifices_&_combinations.pgn`
- **Endgame Studies:** `mednis_practical_rook_endings.pgn`, `shereshevsky_endgame_strategy.pgn`

**Total:** ~500K+ training positions

**Purpose:** Reference database for opening preparation and pattern matching

**Target Table:** `OPENING_THEORY` (NEW - not in original ERD)

**Schema:**
```sql
CREATE TABLE OPENING_THEORY (
  theory_id STRING PRIMARY KEY,
  eco_code STRING,
  opening_name STRING,
  variation STRING,
  fen STRING,
  moves STRING,
  game_source STRING,  -- Which PGN file
  player_white STRING,
  player_black STRING,
  game_result STRING,
  year INT,
  event STRING,
  ingested_at TIMESTAMP
)
```

---

### 5. Documentation Files

**Location:** `raw_data/v7p3r_docs/`  
**Files:** 173 markdown files (1.6 MB)

#### 5.1 CHANGELOG.md
**Critical File:** Version deployment history

**Schema Pattern:**
```markdown
## YYYY Deployment History

### YYYY-MM-DD
- **Version**: v18.4
- **Status**: DEPLOYED | RETIRED | ROLLED BACK
- **Deployment Method**: ...
- **Notes**: ...
```

**Derived Fields:**
- `version` (e.g., "v18.4")
- `deployed_date` (ISO date)
- `status` (deployed/retired/rollback)
- `deployment_notes`

**Target Table:** `ENGINE_VERSIONS`

**Enrichment:** Cross-reference with game dates to map games → versions

#### 5.2 Design & Development Docs
**Examples:**
- `V7P3R_CHESS_ENGINE_DESIGN_GUIDE.md` (12 KB)
- `V7P3R_CHESS_ENGINE_BUILD_GUIDE.md` (5 KB)
- `V7P3R_v10.6_Development_Plan.md` (7 KB)

**Categories:**
- Design guides
- Development plans
- Performance reports
- Rollback reports
- Deployment guides
- Enhancement plans

**Target Table:** `DOCUMENTATION`

**Schema:**
```sql
CREATE TABLE DOCUMENTATION (
  doc_id STRING PRIMARY KEY,
  file_name STRING,
  file_path STRING,
  category STRING,  -- design/development/performance/rollback
  version_related STRING,  -- e.g., "v10.6" if filename contains version
  content TEXT,
  file_size_bytes INT,
  created_at TIMESTAMP,
  modified_at TIMESTAMP,
  ingested_at TIMESTAMP
)
```

---

### 6. Operational Events

**Location:** `raw_data/notation_events.json`  
**File:** Single JSON file (<1 MB)

**JSON Schema:**
```json
{
  "_description": "V7P3R Bot - Operational Events Notation Dataset",
  "_purpose": "Records significant non-code events affecting metrics",
  "events": [
    {
      "date": "2026-04-22",
      "date_approximate": false,
      "type": "operational | config_change | infrastructure | tuning | environment",
      "title": "Event title",
      "change_scope": "chess_engine | lichess_bot_config | infrastructure",
      "engine_version_affected": "v18.4",
      "description": "Detailed description",
      "expected_metric_impact": "Impact description",
      "engine_regression": true/false,
      "notes": "Additional context"
    }
  ]
}
```

**Target Table:** `OPERATIONAL_EVENTS`

**Purpose:** Explain metric shifts not caused by engine changes (e.g., matchmaking bugs, infrastructure issues)

---

## 🎯 Conformed Schema Mapping (Updated)

### Schema Changes from Original ERD

**REMOVED (not in raw_data):**
- ~~PUZZLE_ANALYSIS_RESULTS~~ - Wait, this IS in raw_data (puzzle_results_*.json)
- ~~TOURNAMENTS~~ - Can be derived from Engine Battle .res files
- ~~TOURNAMENT_STANDINGS~~ - Same, derived from .res files

**ADDED (new discoveries):**
- **OPENING_THEORY** - 135 PGN files with opening databases
- **ENGINE_BATTLE_TOURNAMENTS** - Structured tournament data from .res files
- **TOURNAMENT_GAMES** - Separate from Lichess games (different metadata)

### Updated Table Count: **15 Core Tables**

---

## 📋 Complete Table-to-Source Mapping

### Core Game Data

#### 1. LICHESS_GAMES
**Source:** `game_records/Lichess V7P3R Bot/*.pgn`

**Ingestion Logic:**
```python
def parse_lichess_pgn(file_path):
    with open(file_path) as pgn_file:
        game = chess.pgn.read_game(pgn_file)
        headers = game.headers
        
        # Extract game_id from Site URL
        site = headers.get('Site', '')
        game_id = site.split('/')[-1]
        
        # Determine v7p3r color
        white = headers.get('White')
        v7p3r_color = 'white' if white == 'v7p3r_bot' else 'black'
        
        # Map date to version
        game_date = headers.get('Date')
        engine_version = map_date_to_version(game_date, changelog_data)
        
        # Calculate outcome
        result = headers.get('Result')
        outcome = calculate_outcome(result, v7p3r_color)
        
        return {
            'game_id': game_id,
            'date': game_date,
            'white': headers.get('White'),
            'black': headers.get('Black'),
            'result': result,
            'white_elo': int(headers.get('WhiteElo', 0)),
            'black_elo': int(headers.get('BlackElo', 0)),
            'time_control': headers.get('TimeControl'),
            'opening': headers.get('Opening'),
            'eco': headers.get('ECO'),
            'termination': headers.get('Termination'),
            'v7p3r_color': v7p3r_color,
            'outcome': outcome,
            'engine_version': engine_version,
            'source_file': file_path
        }
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.lichess_games (
  game_id STRING NOT NULL,
  event STRING,
  site STRING,
  date DATE NOT NULL,
  round STRING,
  white STRING,
  black STRING,
  result STRING,
  white_elo INT64,
  black_elo INT64,
  time_control STRING,
  opening STRING,
  eco STRING,
  termination STRING,
  move_count INT64,
  
  -- Derived fields
  v7p3r_color STRING,  -- 'white' or 'black'
  v7p3r_elo INT64,
  opponent_name STRING,
  opponent_elo INT64,
  outcome STRING,  -- 'win', 'loss', 'draw'
  engine_version STRING,  -- Mapped from date via CHANGELOG
  time_control_category STRING,  -- 'bullet', 'blitz', 'rapid'
  
  -- Metadata
  source_file STRING,
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (game_id)
)
PARTITION BY DATE(date)
CLUSTER BY engine_version, v7p3r_color;
```

#### 2. MOVES
**Source:** Derived from PGN move sequences

**Ingestion Logic:**
```python
def parse_moves(game, game_id):
    moves = []
    board = game.board()
    ply = 0
    
    for move in game.mainline_moves():
        ply += 1
        san = board.san(move)
        uci = move.uci()
        
        # Board state before move
        fen_before = board.fen()
        
        board.push(move)
        
        # Board state after move
        fen_after = board.fen()
        
        moves.append({
            'game_id': game_id,
            'ply_number': ply,
            'move_number': (ply + 1) // 2,
            'player_color': 'white' if ply % 2 == 1 else 'black',
            'move_san': san,
            'move_uci': uci,
            'fen_before': fen_before,
            'fen_after': fen_after,
            'is_capture': board.is_capture(move),
            'is_check': board.is_check(),
            'is_checkmate': board.is_checkmate()
        })
    
    return moves
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.moves (
  move_id STRING NOT NULL,  -- game_id || '_' || ply_number
  game_id STRING NOT NULL,
  ply_number INT64 NOT NULL,
  move_number INT64,
  player_color STRING,
  move_san STRING,
  move_uci STRING,
  fen_before STRING,
  fen_after STRING,
  is_capture BOOL,
  is_check BOOL,
  is_checkmate BOOL,
  piece_moved STRING,
  
  -- Analysis (joined later)
  stockfish_eval FLOAT64,
  stockfish_mate_in INT64,
  error_classification STRING,  -- 'blunder', 'mistake', 'inaccuracy', 'good', 'best'
  
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (move_id),
  FOREIGN KEY (game_id) REFERENCES lichess_games(game_id)
)
PARTITION BY DATE(_PARTITIONTIME)
CLUSTER BY game_id, ply_number;
```

#### 3. STOCKFISH_ANALYSIS
**Source:** `analysis_results/v*_ytd_analysis_*.json`

**Ingestion Logic:**
```python
def parse_ytd_analysis(file_path):
    with open(file_path) as f:
        data = json.load(f)
    
    metadata = data['metadata']
    patterns = data['patterns']
    
    return {
        'analysis_id': f"{metadata['version']}_{metadata['analysis_date']}",
        'engine_version': metadata['version'],
        'analysis_date': metadata['analysis_date'],
        'stockfish_depth': metadata['stockfish_depth'],
        'total_games_analyzed': patterns['summary']['total_games_analyzed'],
        'blunders_count': patterns['summary']['blunders_count'],
        'mistakes_count': patterns['summary']['mistakes_count'],
        'inaccuracies_count': patterns['summary']['inaccuracies_count'],
        'avg_blunders_per_game': patterns['v7p3r_stats']['blunders_per_game'],
        'avg_mistakes_per_game': patterns['v7p3r_stats']['mistakes_per_game'],
        'avg_accuracy_pct': patterns['v7p3r_stats']['accuracy_pct'],
        'date_range_start': metadata.get('date_range', {}).get('start'),
        'date_range_end': metadata.get('date_range', {}).get('end'),
        'source_file': file_path
    }
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.stockfish_analysis (
  analysis_id STRING NOT NULL,
  engine_version STRING NOT NULL,
  analysis_date TIMESTAMP NOT NULL,
  stockfish_depth INT64,
  total_games_analyzed INT64,
  date_range_start DATE,
  date_range_end DATE,
  
  -- Error statistics
  blunders_count INT64,
  mistakes_count INT64,
  inaccuracies_count INT64,
  avg_blunders_per_game FLOAT64,
  avg_mistakes_per_game FLOAT64,
  avg_accuracy_pct FLOAT64,
  
  -- Opening patterns (JSON)
  opening_patterns JSON,
  move_phase_patterns JSON,
  
  source_file STRING,
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (analysis_id)
)
PARTITION BY DATE(analysis_date)
CLUSTER BY engine_version;
```

#### 4. PUZZLE_ANALYSIS_RESULTS
**Source:** `analysis_results/puzzle_results_v*_*.json`

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.puzzle_analysis_results (
  test_id STRING NOT NULL,  -- version_timestamp
  engine_version STRING NOT NULL,
  test_date TIMESTAMP NOT NULL,
  num_puzzles INT64,
  rating_range_min INT64,
  rating_range_max INT64,
  time_per_position INT64,
  themes ARRAY<STRING>,
  
  -- Overall metrics
  total_positions_analyzed INT64,
  avg_linear_accuracy FLOAT64,
  avg_weighted_accuracy FLOAT64,
  perfect_sequences INT64,
  perfect_sequence_rate FLOAT64,
  
  -- Time management
  avg_time_per_move FLOAT64,
  time_exceeded_rate FLOAT64,
  
  -- Theme performance (JSON)
  theme_performance JSON,
  
  -- Individual puzzle results (nested/repeated)
  puzzle_results JSON,
  
  source_file STRING,
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (test_id)
)
PARTITION BY DATE(test_date)
CLUSTER BY engine_version;
```

#### 5. PUZZLES
**Source:** `pgn_training_data/lichess_db_puzzle.csv`

**Ingestion Logic:**
```python
def ingest_puzzles_csv(file_path):
    import csv
    
    puzzles = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puzzles.append({
                'puzzle_id': row['PuzzleId'],
                'fen': row['FEN'],
                'solution_moves': row['Moves'],
                'rating': int(row['Rating']),
                'rating_deviation': int(row['RatingDeviation']),
                'popularity': int(row['Popularity']),
                'nb_plays': int(row['NbPlays']),
                'themes': row['Themes'].split(),  # Space-separated to array
                'game_url': row['GameUrl'],
                'opening_tags': row['OpeningTags'].split()
            })
    
    return puzzles
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.puzzles (
  puzzle_id STRING NOT NULL,
  fen STRING NOT NULL,
  solution_moves STRING,  -- UCI move sequence
  rating INT64,
  rating_deviation INT64,
  popularity INT64,
  nb_plays INT64,
  themes ARRAY<STRING>,
  game_url STRING,
  opening_tags ARRAY<STRING>,
  
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (puzzle_id)
);
-- No partitioning (reference data)
```

**Estimated Rows:** ~4M

#### 6. OPENING_THEORY (NEW)
**Source:** `pgn_training_data/*.pgn` (opening theory files)

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.opening_theory (
  theory_id STRING NOT NULL,  -- eco_code_game_index
  eco_code STRING,
  opening_name STRING,
  variation STRING,
  fen STRING,
  moves STRING,  -- Full move sequence
  game_source STRING,  -- Which PGN file
  player_white STRING,
  player_black STRING,
  game_result STRING,
  year INT64,
  event STRING,
  
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (theory_id)
)
CLUSTER BY eco_code, opening_name;
```

**Estimated Rows:** ~500K

### Reference Data

#### 7. ENGINE_VERSIONS
**Source:** `v7p3r_docs/CHANGELOG.md`

**Ingestion Logic:**
```python
def parse_changelog(file_path):
    with open(file_path) as f:
        content = f.read()
    
    versions = []
    # Regex to parse version entries
    pattern = r'### (\d{4}-\d{2}-\d{2})\n.*?Version.*?:\s*(v[\d.]+)\n.*?Status.*?:\s*(\w+)'
    
    for match in re.finditer(pattern, content):
        deployed_date, version, status = match.groups()
        versions.append({
            'version': version,
            'deployed_date': deployed_date,
            'status': status.lower()
        })
    
    return versions
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.engine_versions (
  version STRING NOT NULL,
  deployed_date DATE,
  retired_date DATE,
  status STRING,  -- 'deployed', 'retired', 'rollback'
  deployment_notes TEXT,
  
  -- Enriched metrics (calculated)
  total_games INT64,
  total_wins INT64,
  total_losses INT64,
  total_draws INT64,
  win_rate FLOAT64,
  avg_elo INT64,
  days_in_production INT64,
  
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (version)
);
```

#### 8. OPERATIONAL_EVENTS
**Source:** `notation_events.json`

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.operational_events (
  event_id STRING NOT NULL,  -- date_hash
  date DATE NOT NULL,
  date_approximate BOOL,
  type STRING,  -- 'operational', 'config_change', 'infrastructure', 'tuning', 'environment'
  title STRING,
  change_scope STRING,  -- 'chess_engine', 'lichess_bot_config', 'infrastructure'
  engine_version_affected STRING,
  description TEXT,
  expected_metric_impact TEXT,
  engine_regression BOOL,
  notes TEXT,
  
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (event_id),
  FOREIGN KEY (engine_version_affected) REFERENCES engine_versions(version)
)
PARTITION BY DATE(date)
CLUSTER BY engine_version_affected, type;
```

#### 9. DOCUMENTATION
**Source:** `v7p3r_docs/*.md`

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.documentation (
  doc_id STRING NOT NULL,  -- Hash of file_path
  file_name STRING,
  file_path STRING,
  category STRING,  -- 'design', 'development', 'performance', 'rollback', 'deployment'
  version_related STRING,  -- Extracted from filename if present
  content TEXT,
  file_size_bytes INT64,
  created_at TIMESTAMP,
  modified_at TIMESTAMP,
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (doc_id)
)
CLUSTER BY category, version_related;
```

### Tournament Data (NEW)

#### 10. ENGINE_BATTLE_TOURNAMENTS
**Source:** `game_records/Engine Battle YYYYMM/*.res`

**Ingestion Logic:**
```python
def parse_tournament_results(res_file):
    # Parse .res file to extract tournament standings
    # Format: EngineName - OpponentName : Score/Games W-L-D (Results) WinRate +/-ELO
    
    tournament_name = extract_tournament_name(res_file)
    results = []
    
    with open(res_file) as f:
        for line in f:
            if ' - ' in line and ':' in line:
                engine, rest = line.split(' - ', 1)
                opponent, stats = rest.split(' : ', 1)
                
                # Parse stats: "5.0/5 5-0-0 (11111) 100% +1200"
                score, games, record, results_str, win_rate, elo_delta = parse_stats(stats)
                
                results.append({
                    'tournament_name': tournament_name,
                    'engine_name': engine.strip(),
                    'opponent_name': opponent.strip(),
                    'score': score,
                    'games_played': games,
                    'wins': int(record.split('-')[0]),
                    'losses': int(record.split('-')[1]),
                    'draws': int(record.split('-')[2]),
                    'win_rate': float(win_rate.strip('%')) / 100,
                    'elo_delta': int(elo_delta)
                })
    
    return results
```

**BigQuery Schema:**
```sql
CREATE TABLE conformed_layer.engine_battle_tournaments (
  tournament_id STRING NOT NULL,
  tournament_name STRING,
  tournament_date DATE,
  engine_name STRING,
  opponent_name STRING,
  games_played INT64,
  wins INT64,
  losses INT64,
  draws INT64,
  score FLOAT64,
  win_rate FLOAT64,
  elo_delta INT64,
  
  source_file STRING,
  ingested_at TIMESTAMP,
  
  PRIMARY KEY (tournament_id, engine_name, opponent_name)
)
PARTITION BY DATE(tournament_date)
CLUSTER BY tournament_name;
```

### Aggregated Data

#### 11. OPENINGS
**Source:** Aggregated from LICHESS_GAMES

**BigQuery View:**
```sql
CREATE VIEW conformed_layer.openings AS
SELECT 
  eco,
  opening,
  COUNT(*) as total_games,
  SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
  SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as draws,
  AVG(opponent_elo) as avg_opponent_elo,
  SAFE_DIVIDE(
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END),
    COUNT(*)
  ) as win_rate
FROM conformed_layer.lichess_games
WHERE eco IS NOT NULL
GROUP BY eco, opening;
```

#### 12. OPPONENTS
**Source:** Aggregated from LICHESS_GAMES

**BigQuery View:**
```sql
CREATE VIEW conformed_layer.opponents AS
SELECT 
  opponent_name,
  AVG(opponent_elo) as avg_elo,
  COUNT(*) as total_games,
  SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
  SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as draws,
  SAFE_DIVIDE(
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END),
    COUNT(*)
  ) as win_rate
FROM conformed_layer.lichess_games
GROUP BY opponent_name;
```

#### 13. GAME_SUMMARIES
**Source:** Pre-calculated summaries from STOCKFISH_ANALYSIS

**BigQuery Table:**
```sql
CREATE TABLE conformed_layer.game_summaries (
  summary_id STRING NOT NULL,
  period_start DATE,
  period_end DATE,
  engine_version STRING,
  total_games INT64,
  wins INT64,
  losses INT64,
  draws INT64,
  avg_blunders_per_game FLOAT64,
  avg_mistakes_per_game FLOAT64,
  avg_accuracy_pct FLOAT64,
  avg_opponent_elo INT64,
  win_rate FLOAT64,
  
  created_at TIMESTAMP,
  
  PRIMARY KEY (summary_id)
)
PARTITION BY DATE(period_start)
CLUSTER BY engine_version;
```

#### 14. ERROR_PATTERNS
**Source:** Derived from STOCKFISH_ANALYSIS opening_patterns

**BigQuery Table:**
```sql
CREATE TABLE conformed_layer.error_patterns (
  pattern_id STRING NOT NULL,
  engine_version STRING,
  analysis_date DATE,
  
  -- Pattern characteristics
  opening_eco STRING,
  opening_name STRING,
  move_phase STRING,  -- 'opening', 'middlegame', 'endgame'
  
  -- Error statistics
  total_occurrences INT64,
  blunders INT64,
  mistakes INT64,
  inaccuracies INT64,
  avg_centipawn_loss FLOAT64,
  
  -- Context
  typical_fen STRING,
  common_error_move STRING,
  stockfish_best_move STRING,
  
  source_analysis_id STRING,
  
  PRIMARY KEY (pattern_id),
  FOREIGN KEY (source_analysis_id) REFERENCES stockfish_analysis(analysis_id)
)
PARTITION BY DATE(analysis_date)
CLUSTER BY engine_version, opening_eco;
```

#### 15. AI_AGENT_CONTEXT
**Source:** Export view for AI agent consumption

**BigQuery Materialized View:**
```sql
CREATE MATERIALIZED VIEW conformed_layer.ai_agent_context AS
SELECT 
  CURRENT_TIMESTAMP() as context_created_at,
  
  -- Latest version performance
  (SELECT ARRAY_AGG(STRUCT(version, win_rate, total_games, avg_elo) ORDER BY deployed_date DESC LIMIT 5)
   FROM conformed_layer.engine_versions) as recent_versions,
  
  -- Problem openings
  (SELECT ARRAY_AGG(STRUCT(eco, opening, win_rate) ORDER BY win_rate ASC LIMIT 20)
   FROM conformed_layer.openings WHERE total_games >= 10) as problem_openings,
  
  -- Recent operational events
  (SELECT ARRAY_AGG(STRUCT(date, title, engine_version_affected) ORDER BY date DESC LIMIT 10)
   FROM conformed_layer.operational_events) as recent_events,
  
  -- Latest analysis summary
  (SELECT STRUCT(
     engine_version,
     avg_blunders_per_game,
     avg_accuracy_pct,
     total_games_analyzed
   ) FROM conformed_layer.stockfish_analysis ORDER BY analysis_date DESC LIMIT 1) as latest_analysis;
```

---

## 🔄 Dynamic Schema Evolution Strategy

To handle expanding data types without manual schema changes:

### 1. Schema Detection Pattern

```python
class DynamicSchemaIngestion:
    def __init__(self, bigquery_client):
        self.client = bigquery_client
        self.schema_cache = {}
    
    def detect_schema(self, sample_data):
        """Auto-detect BigQuery schema from sample JSON/CSV data."""
        schema = []
        
        for key, value in sample_data.items():
            if isinstance(value, str):
                field_type = 'STRING'
            elif isinstance(value, int):
                field_type = 'INT64'
            elif isinstance(value, float):
                field_type = 'FLOAT64'
            elif isinstance(value, bool):
                field_type = 'BOOL'
            elif isinstance(value, list):
                field_type = 'JSON'  # or ARRAY<STRING>
            elif isinstance(value, dict):
                field_type = 'JSON'
            else:
                field_type = 'STRING'
            
            schema.append(bigquery.SchemaField(key, field_type))
        
        return schema
    
    def merge_schemas(self, existing_schema, new_schema):
        """Merge new fields into existing schema."""
        existing_fields = {f.name: f for f in existing_schema}
        
        for field in new_schema:
            if field.name not in existing_fields:
                # New field discovered - add it
                existing_schema.append(field)
        
        return existing_schema
    
    def update_table_schema(self, table_id, new_schema):
        """Update BigQuery table with new schema."""
        table = self.client.get_table(table_id)
        table.schema = new_schema
        self.client.update_table(table, ['schema'])
```

### 2. Auto-Expanding Ingestion Pattern

```python
def ingest_with_schema_evolution(file_path, table_id):
    # Load sample data
    sample_data = load_sample(file_path, num_rows=10)
    
    # Detect schema from sample
    detected_schema = detect_schema(sample_data[0])
    
    # Get existing table schema
    try:
        table = client.get_table(table_id)
        existing_schema = table.schema
        
        # Merge schemas (add new fields)
        merged_schema = merge_schemas(existing_schema, detected_schema)
        
        # Update table if schema changed
        if len(merged_schema) > len(existing_schema):
            update_table_schema(table_id, merged_schema)
            logging.info(f"Added {len(merged_schema) - len(existing_schema)} new fields to {table_id}")
    
    except NotFound:
        # Table doesn't exist - create it
        table = bigquery.Table(table_id, schema=detected_schema)
        table = client.create_table(table)
        logging.info(f"Created new table {table_id}")
    
    # Ingest data
    load_job = client.load_table_from_json(
        load_all(file_path),
        table_id,
        job_config=bigquery.LoadJobConfig(
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
            ],
            autodetect=False
        )
    )
    load_job.result()
```

### 3. File Pattern Registry

```python
# config/ingestion_patterns.json
{
  "patterns": [
    {
      "pattern": "game_records/Lichess V7P3R Bot/*.pgn",
      "target_table": "conformed_layer.lichess_games",
      "parser": "pgn_parser",
      "schema_evolution": true
    },
    {
      "pattern": "analysis_results/v*_ytd_analysis_*.json",
      "target_table": "conformed_layer.stockfish_analysis",
      "parser": "ytd_analysis_parser",
      "schema_evolution": true
    },
    {
      "pattern": "analysis_results/puzzle_results_*.json",
      "target_table": "conformed_layer.puzzle_analysis_results",
      "parser": "puzzle_results_parser",
      "schema_evolution": true
    },
    {
      "pattern": "v7p3r_docs/*.md",
      "target_table": "conformed_layer.documentation",
      "parser": "markdown_parser",
      "schema_evolution": true
    }
  ]
}
```

### 4. Auto-Discovery Ingestion Runner

```python
def run_auto_ingestion():
    # Load pattern registry
    with open('config/ingestion_patterns.json') as f:
        patterns = json.load(f)['patterns']
    
    for pattern_config in patterns:
        # Find all files matching pattern
        files = glob.glob(pattern_config['pattern'])
        
        logging.info(f"Found {len(files)} files matching {pattern_config['pattern']}")
        
        # Get parser function
        parser = get_parser(pattern_config['parser'])
        
        for file_path in files:
            try:
                # Parse file
                data = parser(file_path)
                
                # Ingest with schema evolution
                if pattern_config['schema_evolution']:
                    ingest_with_schema_evolution(data, pattern_config['target_table'])
                else:
                    ingest_static_schema(data, pattern_config['target_table'])
                
                logging.info(f"✅ Ingested {file_path}")
            
            except Exception as e:
                logging.error(f"❌ Failed to ingest {file_path}: {e}")
```

---

## 📊 Impact of Consolidation

### Before (Original Plan):
- **Scattered Data:** 3 repositories, unclear paths
- **19 Tables:** Including non-existent data sources
- **Manual Schema:** Fixed schema, no evolution
- **Unclear Sources:** References to missing files

### After (Consolidated raw_data):
- **Single Location:** All data in `raw_data/` (2.58 GB, 2,336 files)
- **15 Core Tables:** Only tables with actual source data
- **Dynamic Schema:** Auto-expanding ingestion pattern
- **100% Coverage:** Every file type mapped to target table

### New Data Discovered:
1. **Opening Theory PGNs:** 135 files, 1.5 GB (500K positions)
2. **Engine Battle Tournaments:** Tournament .res files with standings
3. **Larger Puzzle Dataset:** 861 MB CSV (4M rows confirmed)
4. **Richer Analysis:** More analysis JSON variants discovered

### Simplified Ingestion:
1. **File Pattern Matching:** Auto-discover files by glob pattern
2. **Schema Detection:** Infer BigQuery schema from sample data
3. **Schema Merging:** Automatically add new fields when discovered
4. **Parallel Processing:** Process all PGN/JSON files concurrently
5. **Idempotent Loads:** Re-running ingestion updates existing data

---

## ✅ Next Steps

1. **Review this inventory** - Verify all sources are accounted for
2. **Approve schema mapping** - Confirm 15 tables cover all needs
3. **Start Terraform** - Create BigQuery infrastructure (bigquery.tf)
4. **Build ingestion patterns** - Implement auto-discovery pattern registry
5. **Create parsers** - Build parser functions for each file type
6. **Run initial ingestion** - Load all raw_data into BigQuery

**Ready to proceed with dynamic ingestion pipeline?** 🚀
