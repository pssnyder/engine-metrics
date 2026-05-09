# V7P3R Engine Metrics - Complete Data Source Catalog

**Purpose:** Comprehensive inventory of all data sources mapped to conformed BigQuery schema  
**Scope:** All repositories (engine-metrics, engine-tester, v7p3r-chess-engine)  
**Date:** 2026-04-24  
**Status:** Pre-implementation inventory for lakehouse ingestion

---

## 📊 Data Source Summary

| Source Category | Location | Format | Volume | Priority |
|---|---|---|---|---|
| **Lichess Game Records** | `raw_data/game_records/Lichess V7P3R Bot/` | PGN | 50K+ games | **HIGH** |
| **Tournament Game Records** | `raw_data/game_records/Engine Battle YYYYMM/` | PGN | 5K+ games | MEDIUM |
| **Human Game Records** | `raw_data/game_records/v7p3r Human/` | PGN | Small | LOW |
| **Stockfish Analysis Results** | `raw_data/analysis_results/` | JSON | 150+ files | **HIGH** |
| **Puzzle Database** | `../engine-tester/data/puzzles.db` | SQLite | 4M rows | **HIGH** |
| **Puzzle Analysis Results** | `../engine-tester/analysis_results/` | JSON | 890 games | **HIGH** |
| **V7P3R Documentation** | `raw_data/v7p3r_docs/` | Markdown | 184 files | MEDIUM |
| **Notation Events** | `raw_data/notation_events.json` | JSON | 1 file | MEDIUM |
| **Version Changelog** | `../v7p3r-chess-engine/CHANGELOG.md` | Markdown | 1 file | **HIGH** |
| **Deployment Logs** | `../v7p3r-chess-engine/deployment_log.json` | JSON | 1 file | **HIGH** |
| **Testing Scripts Output** | `../v7p3r-chess-engine/testing/` | Various | 95 files | LOW |

**Total Data Volume Estimate:** ~5GB (2GB puzzles + 3GB other sources)  
**BigQuery Storage After Ingestion:** ~8-10GB (with indexes/partitions)

---

## 🗂️ Source-to-Schema Mapping

### 1. LICHESS_GAMES Table

**Source Files:** `raw_data/game_records/Lichess V7P3R Bot/*.pgn`

#### PGN Header → Schema Mapping

| PGN Field | Schema Column | Transformation | Example |
|---|---|---|---|
| `[Event ""]` | `event` | Direct copy | "Rated Blitz game" |
| `[Site ""]` | `site` | Direct copy | "https://lichess.org/abc123" |
| `[Date ""]` | `date` | Parse YYYY.MM.DD | "2026.03.26" |
| `[Round ""]` | `round` | Direct copy | "-" |
| `[White ""]` | `white` | Direct copy | "v7p3r_bot" |
| `[Black ""]` | `black` | Direct copy | "OpponentName" |
| `[Result ""]` | `result` | Direct copy | "1-0" |
| `[WhiteElo ""]` | `white_elo` | Cast to INT | 1467 |
| `[BlackElo ""]` | `black_elo` | Cast to INT | 1523 |
| `[TimeControl ""]` | `time_control` | Direct copy | "180+2" |
| `[ECO ""]` | `eco` | Direct copy | "B20" |
| `[Opening ""]` | `opening` | Direct copy | "Sicilian Defense" |
| `[Termination ""]` | `termination` | Direct copy | "Normal" |
| Move sequence | `moves` | Direct copy | "1. e4 c5 2. Nf3..." |
| - | `game_id` | Extract from Site URL | "abc123" |
| - | `move_count` | Count half-moves | 47 |
| - | `v7p3r_color` | If White == "v7p3r_bot" then "white" | "white" |
| - | `v7p3r_elo` | If v7p3r is White then WhiteElo | 1467 |
| - | `opponent_elo` | Opponent's ELO | 1523 |
| - | `outcome` | Calculate from result+color | "win" |
| - | `engine_version` | Map date → CHANGELOG.md | "v18.3" |
| File path | `source_file` | Full file path | "lichess_v7p3r_bot_2026-03-26.pgn" |
| File mtime | `file_modified_at` | File system timestamp | 2026-03-26T19:15:02 |
| - | `ingested_at` | Current timestamp | 2026-04-24T10:30:00 |

**Additional Processing:**
- **Game Duration:** Parse clock annotations if available, or estimate from move count
- **Version Mapping Logic:**
  1. Extract game date from PGN
  2. Query CHANGELOG.md for version deployed on that date
  3. Assign version (default to "unknown" if no match)

---

### 2. MOVES Table

**Source Files:** Same PGN files as LICHESS_GAMES  
**Extraction Method:** Parse move sequence using python-chess library

#### Move Parsing Logic

```python
# Pseudocode for move extraction
import chess
import chess.pgn

def extract_moves(pgn_string, game_id):
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    board = game.board()
    moves_data = []
    
    for ply_number, move in enumerate(game.mainline_moves(), start=1):
        move_san = board.san(move)
        move_uci = move.uci()
        position_before = board.fen()
        
        board.push(move)
        position_after = board.fen()
        
        # Extract clock time if available
        node = game.variation(0).mainline()[ply_number - 1]
        clock_comment = node.comment  # Parse [%clk 0:03:45]
        
        moves_data.append({
            'move_id': f"{game_id}_{ply_number}",
            'game_id': game_id,
            'ply_number': ply_number,
            'move_number': (ply_number + 1) // 2,
            'player_color': 'white' if ply_number % 2 == 1 else 'black',
            'move_san': move_san,
            'move_uci': move_uci,
            'position_fen': position_after,
            # eval_before, eval_after populated from STOCKFISH_ANALYSIS
            'time_left_ms': parse_clock(clock_comment),
            'ingested_at': datetime.now()
        })
    
    return moves_data
```

#### Schema Columns

| Column | Source | Notes |
|---|---|---|
| `move_id` | Generated | `{game_id}_{ply_number}` |
| `game_id` | FK to LICHESS_GAMES | Parent game |
| `ply_number` | Enumerated | 1, 2, 3, ... |
| `move_number` | Calculated | `(ply + 1) // 2` |
| `player_color` | Calculated | White if odd ply |
| `move_san` | python-chess | "Nf3", "e4" |
| `move_uci` | python-chess | "g1f3", "e2e4" |
| `position_fen` | python-chess | Full FEN after move |
| `eval_before` | Joined from analysis | NULL initially |
| `eval_after` | Joined from analysis | NULL initially |
| `cp_loss` | Calculated | `eval_before - eval_after` |
| `classification` | Calculated | Based on cp_loss thresholds |
| `time_left_ms` | PGN comment parsing | From `[%clk]` annotations |
| `think_time_ms` | Calculated | `prev_time - current_time` |

**Note:** `eval_before`, `eval_after`, `cp_loss`, `classification` populated by joining with STOCKFISH_ANALYSIS results.

---

### 3. STOCKFISH_ANALYSIS Table

**Source Files:** `raw_data/analysis_results/*.json`

#### JSON Structure → Schema Mapping

**Example JSON Structure:**
```json
{
  "metadata": {
    "analysis_date": "2026-04-22T11:19:12.342043",
    "total_games": 1620,
    "stockfish_depth": 18,
    "version": "v18.3",
    "year": 2026
  },
  "patterns": {
    "summary": {
      "total_games_analyzed": 1620,
      "v7p3r_as_white": 771,
      "v7p3r_as_black": 849,
      "total_blunders_white": 11422,
      "total_blunders_black": 10988,
      "total_mistakes_white": 7004,
      "total_mistakes_black": 7327,
      "v7p3r_avg_accuracy": 70.06
    },
    "v7p3r_stats": {
      "blunders_per_game": 6.9,
      "mistakes_per_game": 4.55,
      "total_errors": 18539
    },
    "opening_patterns": {
      "Sicilian Defense": {
        "blunders": 146,
        "mistakes": 108,
        "games": 21
      }
    },
    "move_phase_patterns": {
      "opening": {...},
      "middlegame": {...},
      "endgame": {...}
    }
  }
}
```

#### Schema Mapping

| Schema Column | JSON Path | Notes |
|---|---|---|
| `analysis_id` | Generated | `{version}_{analysis_date}` |
| `game_id` | Multiple | Aggregate analysis (not per-game) |
| `engine_version` | `metadata.version` | "v18.3" |
| `stockfish_depth` | `metadata.stockfish_depth` | 18 |
| `analysis_date` | `metadata.analysis_date` | ISO timestamp |
| `total_moves_analyzed` | Calculated | Sum from games |
| `blunders_count` | `patterns.summary.total_blunders_white + total_blunders_black` | 22410 |
| `mistakes_count` | `patterns.summary.total_mistakes_white + total_mistakes_black` | 14331 |
| `inaccuracies_count` | Calculated | From detailed analysis |
| `accuracy_pct` | `patterns.v7p3r_stats.v7p3r_avg_accuracy` | 70.06 |
| `total_cp_loss` | Calculated | From move-level data |
| `avg_cp_loss` | Calculated | `total_cp_loss / total_moves` |
| `blunders_detail` | `patterns.opening_patterns` + `move_phase_patterns` | JSON |
| `mistakes_detail` | Same | JSON |
| `raw_analysis` | Entire JSON | Full file contents |
| `source_file` | File path | Full path to JSON |
| `ingested_at` | Current timestamp | When imported |

**Note:** Current analysis files are **aggregate** (multiple games). For **per-game analysis**, we'll need to run Stockfish analysis on individual PGN games using Cloud Run.

---

### 4. ERROR_PATTERNS Table

**Source:** Derived from `STOCKFISH_ANALYSIS.blunders_detail` and `mistakes_detail`

#### JSON to Rows Transformation

```python
# Extract opening patterns
for opening_name, stats in analysis_json['patterns']['opening_patterns'].items():
    pattern = {
        'pattern_id': f"{analysis_id}_opening_{slugify(opening_name)}",
        'analysis_id': analysis_id,
        'pattern_type': 'opening',
        'opening_name': opening_name,
        'eco_code': map_opening_to_eco(opening_name),  # Lookup table
        'error_count': stats['blunders'] + stats['mistakes'],
        'blunders': stats['blunders'],
        'mistakes': stats['mistakes'],
        'game_count': stats['games'],
        'avg_errors_per_game': (stats['blunders'] + stats['mistakes']) / stats['games']
    }

# Extract move phase patterns
for phase, stats in analysis_json['patterns']['move_phase_patterns'].items():
    pattern = {
        'pattern_id': f"{analysis_id}_phase_{phase}",
        'analysis_id': analysis_id,
        'pattern_type': 'move_phase',
        'move_range': phase_to_move_range(phase),  # "opening" -> "1-15"
        # ... similar stats
    }
```

---

### 5. ENGINE_VERSIONS Table

**Source:** `../v7p3r-chess-engine/deployment_log.json` + `CHANGELOG.md`

#### deployment_log.json Structure

```json
{
  "deployment_history": [
    {
      "version": "18.3.0",
      "deployed": "2026-03-15",
      "status": "production",
      "environment": "GCP VM (v7p3r-production-bot)",
      "platform": "Lichess (lichess-bot framework)",
      "duration_days": 28,
      "elo_peak": 1523,
      "elo_avg": 1467,
      "changes": [
        "Improved time management",
        "Fixed repetition threshold bug"
      ],
      "regression_tests_passed": true,
      "acceptance_criteria": {
        "win_rate": 0.52,
        "blunders_per_game": 5.1,
        "time_forfeit_rate": 0.08,
        "tested": true
      }
    }
  ]
}
```

#### Schema Mapping

| Schema Column | Source | Notes |
|---|---|---|
| `version_id` | `version` | "v18.3" |
| `deployment_date` | `deployed` | "2026-03-15" |
| `status` | `status` | "DEPLOYED", "RETIRED", etc. |
| `deployment_method` | `environment` | "Automated" or "Manual" |
| `total_games` | Count from LICHESS_GAMES | WHERE engine_version = version |
| `wins` | Count from LICHESS_GAMES | WHERE outcome = 'win' |
| `losses` | Count from LICHESS_GAMES | WHERE outcome = 'loss' |
| `draws` | Count from LICHESS_GAMES | WHERE outcome = 'draw' |
| `win_rate_pct` | Calculated | `wins / total_games * 100` |
| `avg_elo` | `elo_avg` | 1467 |
| `peak_elo` | `elo_peak` | 1523 |
| `retired_date` | Calculated | Next deployment date |
| `retirement_reason` | From CHANGELOG.md | "Regression detected" |
| `notes` | `changes` | JSON array → text |

---

### 6. VERSION_CHANGELOG Table

**Source:** `../v7p3r-chess-engine/CHANGELOG.md`

#### CHANGELOG.md Parsing Logic

**Example Entry:**
```markdown
## [18.3.0] - 2026-03-15

### Changed
- Lowered repetition threshold from 200cp to 50cp

### Rationale
- v17.7 accepting draws at +100cp caused rapid game regression
- 50cp threshold more aggressive

### Testing
- ✅ Regression suite: 100% pass
- ✅ Performance: 52% win rate vs v17.7
```

#### Schema Mapping

| Schema Column | Parsing Logic | Example |
|---|---|---|
| `changelog_id` | `{version}_{section_hash}` | "v18.3_change_001" |
| `version_id` | Extract from `## [VERSION]` | "v18.3" |
| `change_date` | Extract from `- YYYY-MM-DD` | "2026-03-15" |
| `change_type` | Section header | "Changed" → "FEATURE" |
| `title` | Bullet point text | "Lowered repetition threshold" |
| `description` | "Rationale" section | Full text |
| `impact` | "Testing" section | Full text |
| `author` | Git blame or manual | "patss" |
| `technical_details` | Combine sections | JSON object |

---

### 7. OPERATIONAL_EVENTS Table

**Source:** `raw_data/notation_events.json`

#### JSON Structure

```json
{
  "events": [
    {
      "date": "2026-04-22",
      "date_approximate": false,
      "type": "operational",
      "title": "v18.4 monitoring - poor performance observed",
      "change_scope": "chess_engine",
      "engine_version_affected": "v18.4",
      "description": "v18.4 deployed on 2026-04-17. Significant drop in ELO...",
      "expected_metric_impact": "ELO drop starting 2026-04-17",
      "engine_regression": true,
      "notes": "Critical event for understanding performance drop"
    }
  ]
}
```

#### Schema Mapping (Direct 1:1)

| Schema Column | JSON Field |
|---|---|
| `event_id` | Generated |
| `event_date` | `date` |
| `date_approximate` | `date_approximate` |
| `event_type` | `type` |
| `title` | `title` |
| `description` | `description` |
| `change_scope` | `change_scope` |
| `version_affected` | `engine_version_affected` |
| `expected_impact` | `expected_metric_impact` |
| `metadata` | Combine extra fields as JSON |
| `ingested_at` | Current timestamp |

---

### 8. OPENINGS Table

**Source:** Aggregated from LICHESS_GAMES

#### Derivation Logic

```sql
-- Populate OPENINGS table from game data
INSERT INTO openings (eco_code, opening_name, variation, category, ...)
SELECT 
  eco,
  opening,
  NULL as variation,  -- Could parse from opening name
  get_opening_category(eco) as category,  -- UDF based on ECO code
  COUNT(*) as total_games,
  SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as v7p3r_wins,
  SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as v7p3r_losses,
  SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as v7p3r_draws,
  (SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) + 
   SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) * 0.5) / COUNT(*) as success_rate
FROM lichess_games
GROUP BY eco, opening
```

**Additional Fields (from STOCKFISH_ANALYSIS):**
- `avg_cp_loss`: Join with analysis error patterns
- `total_errors`: Sum from error patterns table

---

### 9. OPPONENTS Table

**Source:** Aggregated from LICHESS_GAMES

#### Derivation Logic

```sql
-- Extract opponent data
WITH opponent_games AS (
  SELECT 
    CASE 
      WHEN v7p3r_color = 'white' THEN black 
      ELSE white 
    END as opponent_name,
    opponent_elo,
    date,
    outcome
  FROM lichess_games
)
SELECT 
  opponent_name as opponent_id,
  opponent_name,
  COUNT(*) as games_played,
  SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as v7p3r_wins,
  SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as v7p3r_losses,
  SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as v7p3r_draws,
  MIN(opponent_elo) as min_elo,
  MAX(opponent_elo) as max_elo,
  AVG(opponent_elo) as avg_elo,
  MIN(date) as first_game,
  MAX(date) as last_game
FROM opponent_games
GROUP BY opponent_name
```

---

### 10. DOCUMENTATION Table

**Source:** `raw_data/v7p3r_docs/*.md` + `../v7p3r-chess-engine/docs/*.md`

#### File Processing Logic

```python
import frontmatter
from pathlib import Path

def ingest_documentation(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    # Extract version from filename or content
    version_match = re.search(r'v\d+[\.\d]*', file_path.name)
    version_related = version_match.group(0) if version_match else None
    
    return {
        'doc_id': generate_id(file_path),
        'title': post.metadata.get('title', file_path.stem),
        'content': post.content,
        'doc_type': classify_doc_type(file_path),
        'version_related': version_related,
        'created_date': file_path.stat().st_ctime,
        'modified_date': file_path.stat().st_mtime,
        'tags': post.metadata.get('tags', []),
        'source_file': str(file_path),
        'ingested_at': datetime.now()
    }

def classify_doc_type(file_path):
    name = file_path.name.lower()
    if 'changelog' in name: return 'CHANGELOG'
    if 'design' in name: return 'DESIGN'
    if 'build' in name: return 'BUILD_LOG'
    return 'NOTES'
```

---

### 11. PUZZLE_DATABASE Table (NEW - Not in Current ERD!)

**Source:** `../engine-tester/data/puzzles.db` (SQLite)  
**Volume:** 4 million rows (~2GB)

#### SQLite Schema

```sql
-- Existing puzzles.db schema (discovered from engine-tester)
CREATE TABLE puzzles (
    puzzle_id TEXT PRIMARY KEY,
    fen TEXT NOT NULL,
    moves TEXT NOT NULL,
    rating INTEGER,
    rating_deviation INTEGER,
    popularity INTEGER,
    nb_plays INTEGER,
    themes TEXT,
    game_url TEXT,
    opening_tags TEXT
);
```

#### Proposed BigQuery Schema Addition

**Table: PUZZLES**

| Column | Type | Source | Notes |
|---|---|---|---|
| `puzzle_id` | STRING | `puzzle_id` | Primary key |
| `fen` | STRING | `fen` | Starting position |
| `solution_moves` | STRING | `moves` | UCI notation |
| `rating` | INTEGER | `rating` | Puzzle difficulty |
| `rating_deviation` | INTEGER | `rating_deviation` | Rating uncertainty |
| `popularity` | INTEGER | `popularity` | Play count |
| `nb_plays` | INTEGER | `nb_plays` | Total attempts |
| `themes` | STRING | `themes` | Comma-separated |
| `game_url` | STRING | `game_url` | Source game |
| `opening_tags` | STRING | `opening_tags` | Opening classification |
| `ingested_at` | TIMESTAMP | Current time | Import timestamp |

**Table: PUZZLE_ANALYSIS_RESULTS (NEW)**

| Column | Type | Source | Notes |
|---|---|---|---|
| `analysis_id` | STRING | Generated | PK |
| `puzzle_id` | STRING | FK to PUZZLES | Which puzzle |
| `engine_version` | STRING | Test metadata | "v18.3" |
| `analysis_date` | TIMESTAMP | Test metadata | When analyzed |
| `solved` | BOOLEAN | Test results | TRUE/FALSE |
| `move_sequence` | STRING | Engine output | UCI moves |
| `time_ms` | INTEGER | Test results | Solve time |
| `nodes_searched` | INTEGER | Engine stats | Search effort |
| `eval_score` | FLOAT | Engine eval | Final position eval |
| `is_correct` | BOOLEAN | Compare to solution | Match validation |
| `partial_credit` | FLOAT | If partially correct | 0.0-1.0 |
| `ingested_at` | TIMESTAMP | Current time | Import timestamp |

---

### 12. TOURNAMENT_RESULTS Table (NEW - Not in Current ERD!)

**Source:** `raw_data/game_records/Engine Battle YYYYMM/*.res` files

#### .res File Format (Tournament Results)

```
Rank Name                          Elo    +    - games score oppo. draws
   1 Stockfish 12                  2537  56   54   100   83%  1948   12%
   2 v7p3r_bot                     1467  49   48   100   35%  1948   18%
   3 SlowMate                      1385  48   47   100   28%  1948   15%
```

#### Proposed Schema

**Table: TOURNAMENTS**

| Column | Type | Notes |
|---|---|---|
| `tournament_id` | STRING | Generated from folder name |
| `tournament_name` | STRING | "Engine Battle 202603" |
| `start_date` | DATE | From folder name |
| `end_date` | DATE | File modification date |
| `total_games` | INTEGER | Sum of games |
| `participants` | INTEGER | Count of engines |
| `time_control` | STRING | From .at config file |
| `ingested_at` | TIMESTAMP | Current time |

**Table: TOURNAMENT_STANDINGS**

| Column | Type | Notes |
|---|---|---|
| `standing_id` | STRING | Generated |
| `tournament_id` | STRING | FK to TOURNAMENTS |
| `engine_name` | STRING | "v7p3r_bot" |
| `rank` | INTEGER | Final placement |
| `elo` | INTEGER | Tournament ELO |
| `elo_plus` | INTEGER | ELO uncertainty + |
| `elo_minus` | INTEGER | ELO uncertainty - |
| `games_played` | INTEGER | Total games |
| `score_pct` | FLOAT | Win percentage |
| `opponent_avg` | INTEGER | Average opponent ELO |
| `draw_rate` | FLOAT | Draw percentage |
| `ingested_at` | TIMESTAMP | Current time |

---

## 🔄 Ingestion Script Structure

### Recommended Ingestion Order

```python
# Phase 1: Reference Data (no dependencies)
1. ingest_engine_versions()      # From deployment_log.json + CHANGELOG.md
2. ingest_documentation()         # From v7p3r_docs/
3. ingest_operational_events()   # From notation_events.json
4. ingest_puzzles()              # From puzzles.db (4M rows)

# Phase 2: Game Data (depends on reference data)
5. ingest_lichess_games()        # From PGN files (uses version mapping)
6. ingest_tournament_games()     # From Engine Battle PGNs
7. ingest_tournament_results()   # From .res files

# Phase 3: Derived Move Data (depends on game data)
8. ingest_moves()                # Parse PGN move sequences

# Phase 4: Analysis Data (depends on games + moves)
9. ingest_stockfish_analysis()   # From analysis JSON files
10. ingest_puzzle_analysis()     # From engine-tester analysis results

# Phase 5: Aggregated Tables (depends on all above)
11. build_openings_table()       # Aggregate from games
12. build_opponents_table()      # Aggregate from games
13. build_error_patterns()       # Derive from analysis
14. build_game_summaries()       # Aggregate statistics
```

---

## 📦 Storage Grouping Strategy

### Cloud Storage Bucket Structure

```
gs://v7p3r-raw-data/
├── pgn/
│   ├── lichess/                 # Lichess game records
│   │   └── v7p3r_bot/
│   │       ├── 2026-01/
│   │       ├── 2026-02/
│   │       └── 2026-03/
│   ├── tournaments/             # Engine Battle tournaments
│   │   ├── 202507/
│   │   ├── 202508/
│   │   └── 202603/
│   └── human/                   # Human games (low priority)
│
├── analysis/
│   ├── stockfish/               # Stockfish analysis results
│   │   ├── ytd/
│   │   ├── puzzle/
│   │   └── tournament/
│   └── engine-evals/            # Future GB-scale eval outputs
│
├── puzzles/
│   └── puzzles.db               # 4M puzzle database
│
├── docs/
│   ├── v7p3r/                   # V7P3R documentation
│   └── changelogs/              # CHANGELOG.md + deployment_log.json
│
└── metadata/
    ├── notation_events.json
    └── tournament_configs/      # .at configuration files
```

### BigQuery Dataset Structure

```
chess-engine-metrics-agent
├── raw_layer                    # Raw ingested data (1:1 with sources)
│   ├── pgn_games
│   ├── puzzle_db
│   ├── analysis_json
│   └── documentation
│
├── conformed_layer              # Cleaned, typed, validated data
│   ├── lichess_games           ← Primary table from ERD
│   ├── moves                   ← Primary table from ERD
│   ├── stockfish_analysis      ← Primary table from ERD
│   ├── puzzles                 ← NEW (4M rows)
│   ├── puzzle_analysis         ← NEW
│   ├── tournaments             ← NEW
│   ├── tournament_standings    ← NEW
│   ├── engine_versions         ← From ERD
│   ├── version_changelog       ← From ERD
│   ├── operational_events      ← From ERD
│   ├── documentation           ← From ERD
│   └── error_patterns          ← Derived
│
└── analytics_layer              # Aggregated, ready for queries
    ├── openings                ← Aggregated from games
    ├── opponents               ← Aggregated from games
    ├── game_summaries          ← Periodic aggregations
    ├── version_performance     ← dbt model
    ├── opening_performance     ← dbt model
    └── ai_agent_context        ← Scheduled exports for agent
```

---

## 🎯 Data Coverage Verification

### ERD Coverage Checklist

| ERD Table | Primary Source(s) | Status | Notes |
|---|---|---|---|
| ✅ LICHESS_GAMES | PGN files | **COVERED** | 50K+ games |
| ✅ MOVES | PGN parsing | **COVERED** | Derived from games |
| ✅ STOCKFISH_ANALYSIS | analysis JSON | **COVERED** | 150+ files |
| ✅ ERROR_PATTERNS | analysis JSON | **COVERED** | Derived |
| ✅ ENGINE_VERSIONS | deployment_log.json | **COVERED** | All versions |
| ✅ VERSION_CHANGELOG | CHANGELOG.md | **COVERED** | Full history |
| ✅ OPERATIONAL_EVENTS | notation_events.json | **COVERED** | Complete log |
| ✅ OPENINGS | Derived from games | **COVERED** | Aggregated |
| ✅ OPPONENTS | Derived from games | **COVERED** | Aggregated |
| ✅ DOCUMENTATION | v7p3r_docs/ | **COVERED** | 184 files |
| ✅ GAME_SUMMARIES | Derived | **COVERED** | Calculated |
| ✅ AI_AGENT_CONTEXT | Exported | **COVERED** | Generated |

### Additional Data NOT in ERD (Needs Schema Addition)

| Data Source | Volume | Proposed Table | Priority |
|---|---|---|---|
| **Puzzle Database** | 4M rows | PUZZLES | **HIGH** |
| **Puzzle Analysis** | 890 games | PUZZLE_ANALYSIS_RESULTS | **HIGH** |
| **Tournament Results** | 50+ tournaments | TOURNAMENTS, TOURNAMENT_STANDINGS | MEDIUM |
| **Testing Scripts** | 95 files | TEST_RESULTS | LOW |

---

## 🚀 Next Steps

1. **Update ERD** to include PUZZLES, PUZZLE_ANALYSIS_RESULTS, TOURNAMENTS tables
2. **Create ingestion scripts** for each data source (12 scripts total)
3. **Define BigQuery schemas** with proper partitioning/clustering
4. **Build validation logic** to ensure data quality
5. **Create dbt models** for derived tables
6. **Set up monitoring** for data freshness and completeness

---

**Document Owner:** V7P3R Analytics Team  
**Last Updated:** 2026-04-24  
**Next Review:** After ERD update and schema finalization
