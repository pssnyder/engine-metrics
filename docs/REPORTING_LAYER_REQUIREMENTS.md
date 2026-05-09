# V7P3R Analytics Reporting Layer Requirements

**Version:** 1.0  
**Date:** 2026-04-30  
**Status:** Design Phase

---

## Executive Summary

This document defines the requirements for the **Reporting Layer (Gold)** of the V7P3R Analytics data lakehouse. The reporting layer provides pre-aggregated metrics and KPIs to answer key analytical questions about V7P3R chess engine performance.

**Key Decisions:**
- **2-Tier Architecture:** Tier 1 (Common KPIs) + Tier 2 (Advanced Positional Analysis)
- **Tier 1 Priority:** Build immediately to answer 80% of documented questions
- **Tier 2 Deferred:** Requires Stockfish integration (Phase 4)
- **ETL Pattern:** Manual creation per analytical question (not auto-generated views)
- **Data Governance:** Conformed layer = source of truth, reporting = derived/denormalized

---

## 1. Project Foundation

### 1.1 Original Project Goal

**Objective:** Build a local analytics pipeline that replicates and enhances Lichess Insights functionality.

**Success Criteria** (All Met ✅):
1. ✅ Extract 10,000+ games → **Delivered 18,336 games**
2. ✅ Parse 1M+ moves → **Delivered 1,350,163 moves**
3. ✅ Implement 8+ insight dimensions → **Delivered 10+ dimensions**
4. ✅ ETL performance <10 minutes → **Delivered ~5 minutes**
5. ✅ Version tracking functional → **CHANGELOG-based mapping**
6. ✅ Opening analysis operational → **ECO codes + families**
7. ✅ Multi-dimensional slicing → **Lichess-style framework**

**Achievement:** 80% feature parity with Lichess Insights

### 1.2 Current Data Landscape

**Conformed Layer Status (8/15 tables complete):**
- ✅ documentation (166 files)
- ✅ engine_versions (16 versions)
- ✅ operational_events (8 events)
- ✅ analysis_results (510 files)
- ✅ game_records (24,146 PGN-based games)
- ✅ game_data (18,336 CSV-based games with metadata)
- ✅ game_summary (18,336 tactical summaries: castling, queen trades, opening families)
- ✅ moves (1,350,163 move-level records with material balance, game phase)

**Reporting Layer Status:**
- ❌ Not yet designed (this document defines requirements)

---

## 2. Core Analytical Questions

### 2.1 Performance Analysis Questions

**Engine Version Performance:**
- How has V7P3R improved across versions?
- Which version has the best win rate?
- Are newer versions actually stronger?
- When should users upgrade?

**Documented Insights:**
- v17.1: 70.54% win rate (best version, 224 games)
- v17.5: 41.61% win rate (regression from v17.1)
- Need to identify version upgrade recommendations

**Opponent Strength Analysis:**
- How does V7P3R perform vs different skill levels?
- What is the win rate vs weak (<1400 ELO) opponents?
- Can V7P3R compete with strong (2200+ ELO) opponents?
- Is performance consistent across ELO ranges?

**Documented Insights:**
- 59.80% win rate vs <1400 ELO (strong vs weak players)
- 3.20% win rate vs 2200+ ELO (struggles with masters)
- Significant performance drop-off above 1800 ELO

**Opening Performance:**
- Which openings provide the best advantage?
- Are there openings V7P3R should avoid?
- Does opening choice vary by opponent strength?
- Preferred color (White vs Black) for each opening?

**Documented Insights:**
- Queenside castling: 46.75% win rate
- Kingside castling: 34.49% win rate
- Opening family matters more than ECO code precision

**Time Control Performance:**
- Does V7P3R perform better in bullet, blitz, rapid, or classical?
- Time pressure impact on decision quality?
- Optimal time control for V7P3R?

**Documented Insights:**
- Bullet underperforms vs Rapid/Classical
- Need time-per-move analysis to understand why

### 2.2 Development Questions

**Strategic Questions:**
- What factors most influence V7P3R's performance?
- Which positional types cause the most losses?
- Where should engine development focus?
- What patterns emerge at different skill levels?

**Tactical Questions:**
- Does castling early improve win rates?
- Impact of queen trades on game outcomes?
- Material imbalance handling effectiveness?
- Piece activity and mobility metrics?

**Quality-Adjusted Metrics:**
- Win rate adjusted for opponent strength?
- Performance relative to expected outcome?
- Skill-level-aware benchmarking?

---

## 3. Available Dimensions & Metrics

### 3.1 Implemented Dimensions (From Existing Pipeline)

**Core Dimensions:**
1. **Engine Version** - v14.1, v17.0, v17.1, v17.5, v17.7, etc. (16 versions)
2. **Opponent Strength** - ELO brackets (<1400, 1400-1600, 1600-1800, 1800-2000, 2000-2200, 2200+)
3. **Color** - White, Black
4. **Time Control** - Bullet (<3min), Blitz (3-8min), Rapid (8-25min), Classical (25min+)
5. **Opening Family** - Sicilian, French, Caro-Kann, Queen's Gambit, etc. (19 families)
6. **Castling Pattern** - Kingside, Queenside, None (both V7P3R and opponent)
7. **Queen Trade** - Boolean (whether queens were traded, and on which move)
8. **Temporal** - Daily, Weekly, Monthly aggregations
9. **Termination Type** - Normal, Time forfeit, Resignation, Abandonment
10. **Game Phase** - Opening (≤15 moves), Middlegame (≤40 moves OR material>40), Endgame (else)

### 3.2 Available Metrics (From Existing Pipeline)

**Game Outcome Metrics:**
- Win Rate (%)
- Loss Rate (%)
- Draw Rate (%)
- Games Played (count)

**Performance Metrics:**
- Average Game Length (moves)
- Average ELO (V7P3R's rating)
- Average Opponent ELO
- Average Rating Difference (V7P3R - Opponent)
- Average ELO Change (+/- points per game)

**Positional Metrics (Move-Level Data):**
- Material Balance (white_material - black_material)
- Piece Activity (moves per piece type)
- Capture Frequency
- Check Frequency
- Castling Timing (move number)
- Queen Trade Timing (move number)

### 3.3 Missing Metrics (Require Stockfish Integration)

**Quality Metrics (Phase 4):**
- Move Accuracy (centipawn loss)
- Blunder Rate (moves losing ≥200cp)
- Mistake Rate (moves losing 100-199cp)
- Inaccuracy Rate (moves losing 50-99cp)
- Average Centipawn Loss per Move

**Position Evaluation Metrics:**
- Position Complexity (number of legal moves)
- King Safety Score
- Piece Coordination Score
- Pawn Structure Quality

---

## 4. Reporting Layer Architecture

### 4.1 Two-Tier Design

**Tier 1: Common Chess KPIs** (Priority: HIGH, Implement Immediately)
- **Purpose:** Pre-aggregated metrics for 80% of analytical questions
- **Audience:** Dashboard visualizations, quick queries, trend analysis
- **Data Sources:** game_data, game_summary, game_records (conformed layer)
- **ETL Pattern:** Daily batch jobs or materialized views
- **Performance Target:** Queries return in <1 second
- **7 Tables Defined** (see Section 5)

**Tier 2: Advanced Positional Analysis** (Priority: LOW, Deferred to Phase 4)
- **Purpose:** Deep analysis linking positions → moves → outcomes → skill levels
- **Audience:** Engine development, weakness detection, training data
- **Data Sources:** moves + Stockfish analysis (requires Phase 4 integration)
- **ETL Pattern:** On-demand batch jobs (computationally expensive)
- **Performance Target:** Queries may take 10-60 seconds (complex aggregations)
- **6 Tables Defined** (see Section 6)

### 4.2 ETL Execution Model

**Manual ETL Creation (Not Auto-Generated Views):**
- Each analytical question triggers new ETL script creation
- Workflow: Question → Verify data exists → Create ETL → Create table
- ETL scripts stored in `scripts/reporting_etl/`
- Example: `01_generate_version_performance.py`

**Rationale:**
- Aligns with data governance model (conformed = truth, reporting = derived)
- Avoids over-engineering unused metrics
- Purpose-built for specific use cases
- Allows per-use-case optimization (real-time vs batch)

**Refresh Cadence:**
- **Tier 1 Tables:** Daily refresh (via Cloud Scheduler or cron)
- **Tier 2 Tables:** On-demand refresh (triggered manually or by new Stockfish analysis)
- **Exception:** Real-time needs (live dashboards) use materialized views

---

## 5. Tier 1 Reporting Tables (Common KPIs)

### 5.1 Table: version_performance_summary

**Purpose:** Aggregate V7P3R performance by engine version for version comparison and upgrade recommendations.

**Schema:**
```sql
CREATE TABLE reporting_layer.version_performance_summary (
  engine_version STRING NOT NULL,          -- v14.1, v17.0, v17.1, etc.
  total_games INT64 NOT NULL,              -- Count of games played
  wins INT64 NOT NULL,                     -- Games won
  losses INT64 NOT NULL,                   -- Games lost
  draws INT64 NOT NULL,                    -- Games drawn
  win_rate FLOAT64 NOT NULL,               -- wins / total_games
  loss_rate FLOAT64 NOT NULL,              -- losses / total_games
  draw_rate FLOAT64 NOT NULL,              -- draws / total_games
  avg_v7p3r_elo FLOAT64,                   -- Average V7P3R ELO during this version
  avg_opponent_elo FLOAT64,                -- Average opponent ELO faced
  avg_rating_diff FLOAT64,                 -- Average (V7P3R - Opponent) ELO
  avg_game_length FLOAT64,                 -- Average moves per game
  time_period_start DATE,                  -- First game date for this version
  time_period_end DATE,                    -- Last game date for this version
  games_as_white INT64,                    -- Games played as White
  games_as_black INT64,                    -- Games played as Black
  white_win_rate FLOAT64,                  -- Win rate when playing White
  black_win_rate FLOAT64,                  -- Win rate when playing Black
  last_updated TIMESTAMP                   -- ETL run timestamp
);
```

**Source Data:** 
- `conformed_layer.game_data` (game_id, engine_version, outcome, result, color, v7p3r_elo, opponent_elo, move_count, date)

**Sample Analytical Queries:**
- Best version by win rate: `SELECT * FROM version_performance_summary ORDER BY win_rate DESC LIMIT 5`
- Version regression detection: Compare win_rate across sequential versions
- Upgrade recommendations: Identify versions with win_rate > current version

---

### 5.2 Table: opponent_strength_performance

**Purpose:** Analyze V7P3R performance across opponent ELO brackets to identify strengths and weaknesses by skill level.

**Schema:**
```sql
CREATE TABLE reporting_layer.opponent_strength_performance (
  elo_bracket STRING NOT NULL,             -- '<1400', '1400-1600', '1600-1800', '1800-2000', '2000-2200', '2200+'
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_game_length FLOAT64,
  avg_rating_diff FLOAT64,                 -- Average ELO advantage/disadvantage
  games_as_white INT64,
  games_as_black INT64,
  white_win_rate FLOAT64,
  black_win_rate FLOAT64,
  color_balance FLOAT64,                   -- white_win_rate - black_win_rate (detect color bias)
  avg_elo_change FLOAT64,                  -- Average rating gain/loss per game
  quality_adjusted_win_rate FLOAT64,       -- Win rate weighted by opponent strength
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_data` (opponent_elo, outcome, color, rating_diff, move_count)

**Bucketing Logic:**
```python
elo_brackets = {
  '<1400': (0, 1399),
  '1400-1600': (1400, 1599),
  '1600-1800': (1600, 1799),
  '1800-2000': (1800, 1999),
  '2000-2200': (2000, 2199),
  '2200+': (2200, 9999)
}
```

**Sample Analytical Queries:**
- Performance vs strong players: `SELECT * FROM opponent_strength_performance WHERE elo_bracket IN ('2000-2200', '2200+')`
- Skill level progression: Plot win_rate by elo_bracket
- Color imbalance detection: `SELECT elo_bracket, color_balance FROM opponent_strength_performance WHERE ABS(color_balance) > 0.10`

---

### 5.3 Table: opening_performance

**Purpose:** Evaluate opening repertoire effectiveness by opening family and ECO code.

**Schema:**
```sql
CREATE TABLE reporting_layer.opening_performance (
  opening_family STRING NOT NULL,          -- 'Sicilian Defense', 'French Defense', 'Queen\'s Gambit', etc.
  eco_code STRING,                         -- 'B20', 'C00', 'D06', etc. (NULL if not mapped)
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_opponent_elo FLOAT64,
  games_as_white INT64,
  games_as_black INT64,
  preferred_color STRING,                  -- 'white', 'black', or 'balanced' (most games played)
  white_win_rate FLOAT64,
  black_win_rate FLOAT64,
  avg_game_length FLOAT64,
  avg_v7p3r_castled STRING,                -- Most common castling: 'kingside', 'queenside', 'none'
  avg_opponent_castled STRING,
  queen_trade_rate FLOAT64,                -- % of games with queen trade
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_data` (eco, opening)
- `conformed_layer.game_summary` (opening_family, v7p3r_castled, opponent_castled, queen_traded)

**Sample Analytical Queries:**
- Best openings: `SELECT opening_family, win_rate FROM opening_performance WHERE total_games >= 50 ORDER BY win_rate DESC LIMIT 10`
- Openings to avoid: `SELECT opening_family, win_rate FROM opening_performance WHERE total_games >= 50 ORDER BY win_rate ASC LIMIT 10`
- Color-specific openings: `SELECT opening_family, preferred_color FROM opening_performance WHERE ABS(games_as_white - games_as_black) > 20`

---

### 5.4 Table: time_control_performance

**Purpose:** Compare V7P3R performance across time control formats (Bullet, Blitz, Rapid, Classical).

**Schema:**
```sql
CREATE TABLE reporting_layer.time_control_performance (
  time_control_category STRING NOT NULL,   -- 'bullet', 'blitz', 'rapid', 'classical'
  time_control_range STRING,               -- '<3min', '3-8min', '8-25min', '25min+'
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_game_length FLOAT64,
  avg_v7p3r_elo FLOAT64,
  avg_opponent_elo FLOAT64,
  games_as_white INT64,
  games_as_black INT64,
  color_balance FLOAT64,                   -- white_win_rate - black_win_rate
  avg_elo_change FLOAT64,
  time_forfeit_rate FLOAT64,               -- % of games lost by time
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_data` (time_control, outcome, termination, color)

**Categorization Logic:**
```python
time_categories = {
  'bullet': lambda tc: total_seconds(tc) < 180,        # <3 minutes
  'blitz': lambda tc: 180 <= total_seconds(tc) < 480,  # 3-8 minutes
  'rapid': lambda tc: 480 <= total_seconds(tc) < 1500, # 8-25 minutes
  'classical': lambda tc: total_seconds(tc) >= 1500    # 25+ minutes
}
```

**Sample Analytical Queries:**
- Best time control: `SELECT time_control_category, win_rate FROM time_control_performance ORDER BY win_rate DESC`
- Time pressure impact: `SELECT time_control_category, time_forfeit_rate FROM time_control_performance`

---

### 5.5 Table: temporal_trends

**Purpose:** Track performance trends over time (daily, weekly, monthly) for ELO progression and version impact analysis.

**Schema:**
```sql
CREATE TABLE reporting_layer.temporal_trends (
  date_period DATE NOT NULL,               -- Aggregation date (day, start of week, start of month)
  period_type STRING NOT NULL,             -- 'daily', 'weekly', 'monthly'
  engine_version STRING,                   -- Dominant version during this period
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_v7p3r_elo FLOAT64,                   -- Average ELO during period
  elo_start FLOAT64,                       -- ELO at period start
  elo_end FLOAT64,                         -- ELO at period end
  elo_change FLOAT64,                      -- elo_end - elo_start
  avg_opponent_elo FLOAT64,
  avg_game_length FLOAT64,
  games_per_day FLOAT64,                   -- total_games / days_in_period
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_data` (date, time, engine_version, outcome, v7p3r_elo, opponent_elo, move_count)

**Sample Analytical Queries:**
- Monthly performance: `SELECT date_period, win_rate FROM temporal_trends WHERE period_type = 'monthly' ORDER BY date_period`
- ELO progression: `SELECT date_period, elo_change FROM temporal_trends WHERE period_type = 'weekly'`
- Best performance month: `SELECT date_period, win_rate FROM temporal_trends WHERE period_type = 'monthly' ORDER BY win_rate DESC LIMIT 1`

---

### 5.6 Table: castling_analysis

**Purpose:** Analyze impact of castling patterns (kingside vs queenside vs none) on game outcomes.

**Schema:**
```sql
CREATE TABLE reporting_layer.castling_analysis (
  v7p3r_castling STRING NOT NULL,          -- 'kingside', 'queenside', 'none'
  opponent_castling STRING NOT NULL,       -- 'kingside', 'queenside', 'none'
  castling_pattern STRING NOT NULL,        -- Combined: 'v7p3r_kingside_opp_kingside', etc.
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_opponent_elo FLOAT64,
  avg_game_length FLOAT64,
  avg_v7p3r_castle_move INT64,            -- Average move number when V7P3R castled (NULL if none)
  avg_opponent_castle_move INT64,         -- Average move number when opponent castled
  queen_trade_rate FLOAT64,               -- % of games with queen trade
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_summary` (v7p3r_castled, opponent_castled, queen_traded, total_moves)
- `conformed_layer.moves` (to find castling move number via is_castle=TRUE)

**Sample Analytical Queries:**
- Queenside advantage: `SELECT v7p3r_castling, win_rate FROM castling_analysis GROUP BY v7p3r_castling ORDER BY win_rate DESC`
- Castling pattern matchups: `SELECT castling_pattern, win_rate FROM castling_analysis WHERE total_games >= 20 ORDER BY win_rate DESC`

---

### 5.7 Table: queen_trade_analysis

**Purpose:** Evaluate impact of queen trades on game outcomes and strategic implications.

**Schema:**
```sql
CREATE TABLE reporting_layer.queen_trade_analysis (
  queen_traded BOOLEAN NOT NULL,           -- TRUE if queens traded, FALSE otherwise
  trade_move_bucket STRING,                -- 'early' (≤20 moves), 'mid' (21-40), 'late' (41+), NULL if no trade
  total_games INT64 NOT NULL,
  wins INT64 NOT NULL,
  losses INT64 NOT NULL,
  draws INT64 NOT NULL,
  win_rate FLOAT64 NOT NULL,
  avg_trade_move FLOAT64,                  -- Average move number when trade occurred (NULL if no trade)
  avg_game_length FLOAT64,
  avg_opponent_elo FLOAT64,
  opening_family_distribution JSON,        -- Top 5 openings for this trade pattern: [{"opening": "Sicilian", "count": 50}, ...]
  avg_material_balance FLOAT64,            -- Average material balance when trade occurred
  last_updated TIMESTAMP
);
```

**Source Data:**
- `conformed_layer.game_summary` (queen_traded, queen_traded_move, opening_family)
- `conformed_layer.game_data` (outcome, opponent_elo, move_count)
- `conformed_layer.moves` (material_balance at queen_traded_move)

**Sample Analytical Queries:**
- Impact of queen trades: `SELECT queen_traded, win_rate FROM queen_trade_analysis`
- Optimal trade timing: `SELECT trade_move_bucket, win_rate FROM queen_trade_analysis WHERE queen_traded = TRUE`

---

## 6. Tier 2 Reporting Tables (Advanced Positional Analysis)

**Status:** DEFERRED - Requires Stockfish Integration (Phase 4)

### 6.1 Table: move_quality_by_position

**Purpose:** Analyze move accuracy by position type and game phase.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.move_quality_by_position (
  position_hash STRING NOT NULL,           -- FEN hash or position signature
  move_number_bucket STRING NOT NULL,      -- '1-10', '11-20', '21-30', '31-40', '41+'
  game_phase STRING NOT NULL,              -- 'opening', 'middlegame', 'endgame'
  avg_material_balance FLOAT64,
  move_frequency INT64,                    -- How often this position appears
  avg_centipawn_loss FLOAT64,              -- Requires Stockfish
  blunder_rate FLOAT64,                    -- % of moves with ≥200cp loss
  win_rate_after_move FLOAT64,            -- Win rate in games with this position
  common_piece_moved STRING,               -- Most frequent piece moved (N, B, R, Q, K, P)
  opponent_elo_range STRING,               -- '<1600', '1600-2000', '2000+'
  last_updated TIMESTAMP
);
```

**Dependencies:** Stockfish move-by-move evaluation (centipawn loss)

---

### 6.2 Table: positional_weakness_patterns

**Purpose:** Identify positions where V7P3R frequently loses or draws.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.positional_weakness_patterns (
  position_type STRING NOT NULL,           -- 'opening', 'middlegame', 'endgame'
  material_balance_range STRING NOT NULL,  -- '-5 to -1', '0', '+1 to +5', etc.
  common_mistakes JSON,                    -- [{"piece": "N", "mistake_type": "blunder", "count": 15}, ...]
  frequency INT64,                         -- How often this pattern occurs
  loss_rate FLOAT64,                       -- % of games lost from this position
  opponent_elo_range STRING,
  engine_version STRING,                   -- Version where pattern observed
  sample_game_ids JSON,                    -- [game_id1, game_id2, ...] for review
  last_updated TIMESTAMP
);
```

**Dependencies:** Stockfish evaluation, position classification

---

### 6.3 Table: skill_level_correlations

**Purpose:** Link performance patterns to opponent skill levels.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.skill_level_correlations (
  opponent_elo_bracket STRING NOT NULL,
  preferred_openings JSON,                 -- [{"opening": "Sicilian", "games": 50, "win_rate": 0.60}, ...]
  common_positions_encountered JSON,       -- FEN array of frequent positions
  win_rate FLOAT64,
  avg_move_time FLOAT64,                   -- Requires clock data
  game_phase_performance JSON,             -- {"opening": 0.55, "middlegame": 0.48, "endgame": 0.42}
  blunder_rate_by_phase JSON,              -- {"opening": 0.05, "middlegame": 0.12, "endgame": 0.08}
  last_updated TIMESTAMP
);
```

**Dependencies:** Stockfish analysis, clock time aggregation

---

### 6.4 Table: piece_activity_metrics

**Purpose:** Track piece usage and effectiveness.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.piece_activity_metrics (
  piece_type STRING NOT NULL,              -- 'N', 'B', 'R', 'Q', 'K', 'P'
  game_phase STRING NOT NULL,              -- 'opening', 'middlegame', 'endgame'
  avg_moves_per_game FLOAT64,              -- How often piece moves
  capture_frequency FLOAT64,               -- % of moves that are captures
  win_rate_when_active FLOAT64,            -- Win rate when piece makes ≥3 moves
  opponent_elo_range STRING,
  avg_centralization_score FLOAT64,        -- Requires position evaluation
  last_updated TIMESTAMP
);
```

**Dependencies:** Position evaluation, piece square tables

---

### 6.5 Table: material_imbalance_outcomes

**Purpose:** Analyze performance with material advantage/disadvantage.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.material_imbalance_outcomes (
  material_balance_range STRING NOT NULL,  -- '-10 to -6', '-5 to -1', '0', '+1 to +5', '+6 to +10'
  game_phase STRING NOT NULL,              -- 'opening', 'middlegame', 'endgame'
  total_positions INT64,                   -- How many times this imbalance occurred
  win_rate FLOAT64,
  draw_rate FLOAT64,
  loss_rate FLOAT64,
  avg_moves_to_resolution FLOAT64,         -- How many moves until game ends
  conversion_rate FLOAT64,                 -- Win rate when ahead ≥2 pawns
  defense_rate FLOAT64,                    -- Draw rate when behind ≥2 pawns
  last_updated TIMESTAMP
);
```

**Dependencies:** Material balance tracking (already available from moves table)

---

### 6.6 Table: time_pressure_analysis

**Purpose:** Evaluate decision quality under time pressure.

**Schema** (Preliminary):
```sql
CREATE TABLE reporting_layer.time_pressure_analysis (
  time_remaining_bucket STRING NOT NULL,   -- '>5min', '3-5min', '1-3min', '30s-1min', '<30s'
  game_phase STRING NOT NULL,              -- 'opening', 'middlegame', 'endgame'
  move_quality STRING,                     -- 'best', 'good', 'inaccurate', 'mistake', 'blunder' (Stockfish)
  total_moves INT64,
  blunder_rate FLOAT64,                    -- % of moves that are blunders
  avg_centipawn_loss FLOAT64,              -- Requires Stockfish
  win_rate FLOAT64,                        -- Win rate for games with this time pressure
  time_forfeit_rate FLOAT64,               -- % of games lost by time
  last_updated TIMESTAMP
);
```

**Dependencies:** Clock time data (partially available), Stockfish move quality

---

## 7. Data Governance Model

### 7.1 Source of Truth Principle

**Conformed Layer = Source of Truth:**
- All analytical queries ultimately derive from conformed layer tables
- If reporting layer conflicts with conformed layer, conformed wins
- Reporting tables can be dropped and rebuilt from conformed layer without data loss

**Reporting Layer = Derived/Denormalized:**
- Pre-aggregated for query performance
- Denormalized to avoid complex joins in dashboard queries
- Purpose-built for specific analytical questions

### 7.2 Automation Rules

**Raw → Conformed Flow: AUTOMATED (after initial setup)**
- PGN files uploaded to GCS trigger automated ingestion
- Analysis JSON files trigger automated parsing
- Validation against source data contracts (reject invalid files)
- Append-only ingestion (no updates to historical records)

**Conformed → Reporting Flow: MANUAL ETL PER QUESTION**
- New analytical question → Create new ETL script
- ETL script queries conformed layer → Writes to reporting table
- Scheduled refresh (daily for Tier 1, on-demand for Tier 2)
- ETL scripts stored in `scripts/reporting_etl/`

### 7.3 Source Data Contracts

**Purpose:** Define expected schema and validation rules for raw data sources.

**Contracts to Create:**
1. **pgn_game_source_contract.md** - PGN file format
   - Required fields: Event, Site, Date, White, Black, Result, moves
   - Optional fields: WhiteElo, BlackElo, TimeControl, ECO, Opening
   - Expansion rules: New PGN headers allowed, existing fields immutable
   
2. **json_analysis_source_contract.md** - Stockfish analysis JSON
   - Required fields: game_id, fen, move, score, depth
   - Optional fields: nodes, time, pv (principal variation)
   - Expansion rules: Additional analysis fields welcome
   
3. **changelog_version_source_contract.md** - CHANGELOG version mapping
   - Required fields: version_number, release_date, description
   - Optional fields: deployment_status, elo_estimate
   - Expansion rules: New fields allowed, version history immutable

### 7.4 ETL Script Naming Convention

**Pattern:** `{sequence}_{action}_{entity}.py`

**Examples:**
- `01_generate_version_performance.py` - First Tier 1 table
- `02_generate_opponent_strength.py` - Second Tier 1 table
- `06_generate_castling_analysis.py` - Sixth Tier 1 table
- `11_generate_move_quality.py` - First Tier 2 table (deferred)

**Sequence Numbers:**
- 01-10: Tier 1 reporting tables
- 11-20: Tier 2 reporting tables
- 21+: Custom one-off analyses

---

## 8. Implementation Roadmap

### Phase 2.1: Requirements Documentation ✅ COMPLETE
- ✅ Document project goals and analytical questions
- ✅ Define 2-tier architecture
- ✅ Specify 7 Tier 1 table schemas
- ✅ Specify 6 Tier 2 table schemas (deferred)
- ✅ Define data governance model

### Phase 2.2: Design Tier 1 Schemas (NEXT)
- Create Terraform schemas for 7 Tier 1 tables
- File: `terraform/reporting_*.tf` (one per table)
- Apply Terraform to create reporting tables

### Phase 2.3: Design Tier 2 Schemas (DEFERRED)
- Create placeholder Terraform schemas for Tier 2
- Mark as DEFERRED in comments
- Wait for Stockfish integration before implementation

### Phase 2.4: Create Data Governance Documentation
- Document: `docs/DATA_GOVERNANCE_MODEL.md`
- Document: `contracts/pgn_game_source_contract.md`
- Document: `contracts/json_analysis_source_contract.md`
- Document: `contracts/changelog_version_source_contract.md`

### Phase 3: Implement Tier 1 ETLs
- Create 7 Python ETL scripts
- Execute ETLs to populate reporting tables
- Validate aggregation correctness
- Document in `docs/REPORTING_LAYER_DATA_DICTIONARY.md`

### Phase 4: Stockfish Integration (Future)
- Build Stockfish analysis pipeline
- Populate move quality data
- Implement Tier 2 ETLs
- Update reporting layer documentation

---

## 9. Success Criteria

**Phase 2 Complete When:**
- ✅ REPORTING_LAYER_REQUIREMENTS.md created and approved
- ✅ 7 Tier 1 tables fully specified (schemas defined)
- ✅ 6 Tier 2 tables outlined (deferred with dependencies documented)
- ✅ Data governance model documented
- ✅ ETL naming conventions established

**Phase 3 Complete When:**
- ✅ All 7 Tier 1 tables exist in BigQuery
- ✅ All 7 ETL scripts executable and tested
- ✅ Sample analytical queries return correct results
- ✅ Query performance meets <1 second target
- ✅ Reporting layer documentation complete

**Validation Queries:**
1. "What is V7P3R's win rate vs 2000+ ELO opponents?" → Query opponent_strength_performance
2. "Which openings perform best?" → Query opening_performance ORDER BY win_rate DESC
3. "How has ELO trended over time?" → Query temporal_trends
4. "Does castling queenside improve win rate?" → Query castling_analysis

---

## 10. Future Enhancements

**Post-Phase 3 Considerations:**
1. **Web Dashboard:** Interactive visualizations (Streamlit/Looker Studio)
2. **Real-time Updates:** Streaming ingestion for live game tracking
3. **ML Predictions:** Opening recommendation engine, opponent pattern detection
4. **API Layer:** RESTful API for third-party integrations
5. **Alerting:** Slack/email notifications for performance regressions

**Post-Phase 4 (Stockfish Integration):**
1. **Tier 2 Table Implementation:** All 6 positional analysis tables
2. **Training Data Generation:** Export positions for neural network training
3. **Automated Weakness Detection:** Alert on recurring blunder patterns
4. **Position Clustering:** Group similar positions for repertoire optimization

---

## Appendix A: Comparison to Lichess Insights

| Feature | Lichess | V7P3R Tier 1 | V7P3R Tier 2 | Status |
|---------|---------|--------------|--------------|--------|
| Game Metadata | ✅ | ✅ | - | Complete |
| Opponent Strength Analysis | ✅ | ✅ | - | Complete |
| Opening Performance | ✅ | ✅ | - | Complete |
| Castling Patterns | ✅ | ✅ | - | Complete |
| Queen Trade Analysis | ✅ | ✅ | - | Complete |
| Time Control Comparison | ✅ | ✅ | - | Complete |
| Color Performance | ✅ | ✅ | - | Complete |
| Temporal Trends | ✅ | ✅ | - | Complete |
| Move Time Analysis | ✅ | - | ✅ | Phase 4 |
| Move Accuracy | ✅ | - | ✅ | Phase 4 |
| Positional Weakness Detection | ❌ | - | ✅ | Enhanced (Phase 4) |
| Material Imbalance Handling | ❌ | - | ✅ | Enhanced (Phase 4) |
| Piece Activity Metrics | ❌ | - | ✅ | Enhanced (Phase 4) |
| Skill Level Correlations | ❌ | - | ✅ | Enhanced (Phase 4) |

**Achievement:** 100% parity for Tier 1, surpasses Lichess with Tier 2

---

## Appendix B: Glossary

**Conformed Layer:** Cleaned, validated, structured data (source of truth)  
**Reporting Layer:** Pre-aggregated, denormalized metrics (derived from conformed)  
**ETL:** Extract-Transform-Load (data pipeline script)  
**ELO:** Chess rating system (higher = stronger player)  
**ECO:** Encyclopedia of Chess Openings classification code  
**SAN:** Standard Algebraic Notation (chess move format)  
**FEN:** Forsyth-Edwards Notation (chess position format)  
**Centipawn Loss:** Stockfish measure of move quality (100 centipawns = 1 pawn)  
**Blunder:** Move losing ≥200 centipawns  
**Opening Family:** Group of related openings (e.g., all Sicilian variations)  
**Game Phase:** Opening (≤15 moves), Middlegame (≤40 moves), Endgame (else)  
**Material Balance:** white_material - black_material (positive = White ahead)  

---

**Document Owner:** V7P3R Analytics Team  
**Last Updated:** 2026-04-30  
**Next Review:** After Phase 3 completion
