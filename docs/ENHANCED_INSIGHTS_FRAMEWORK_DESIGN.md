# V7P3R Chess Engine - Enhanced Insights Framework Design

**Goal:** Replicate and enhance Lichess Insights functionality with multi-dimensional analytics

**Generated:** 2026-03-26

---

## Current State

### ✅ Completed (Phase 1)
1. **ETL Pipeline** - `extract_game_data.py`
   - Extracts game-level metadata from PGN files
   - Maps games to engine versions via CHANGELOG
   - Outputs conformed CSV dataset (18,336 games)

2. **Basic Reporting** - `generate_gameplay_report.py`
   - Overall performance metrics
   - Color performance analysis
   - ELO statistics
   - Time control performance
   - Opening performance (top 10)
   - Version comparison

### ⚠️ Limitations
- **Game-level only**: No move-by-move analysis
- **No derived metrics**: Can't calculate castling, queen trades, material imbalance
- **No position analysis**: Can't determine game phase, winning chances, accuracy
- **Static reports**: No interactive slicing/filtering

---

## Enhanced Insights Architecture

### Data Dimensions (Lichess-Compatible)

#### 1. Setup Dimensions (Game Metadata)
- ✅ **Date** - Already captured
- ✅ **Variant** - From PGN Event header (Standard, Rapid, Blitz, etc.)
- ✅ **Color** - White/Black
- ✅ **Opponent Strength** - Derived from opponent ELO (buckets: <1400, 1400-1600, 1600-1800, 1800-2000, 2000+)
- ⚠️ **Game Source** - Need to parse Site header (Lichess, Chess.com, etc.)

#### 2. Game Dimensions (Position-Based)
- ⚠️ **Opening Family** - Need ECO grouping (e.g., "Sicilian Defense" from ECO B20-B99)
- ✅ **Opening Variation** - Already captured in PGN headers
- ❌ **My Castling Side** - Requires move parsing (O-O vs O-O-O vs none)
- ❌ **Opponent Castling Side** - Requires move parsing
- ❌ **Queen Trade** - Requires move parsing (detect Qxd8+ Qxd8 patterns)

#### 3. Move Dimensions (Requires Engine Analysis)
- ❌ **Piece Moved** - Parse SAN notation (e.g., N, B, R, Q, K, pawn)
- ❌ **Move Time** - Parse clock annotations [%clk 0:05:00]
- ❌ **Time Pressure** - Derived from clock (e.g., <30s remaining)
- ❌ **Material Imbalance** - Track material count per move
- ❌ **Accuracy** - Requires Stockfish analysis (compare engine move to best move)
- ❌ **Winning Chances** - Requires Stockfish centipawn evaluation
- ❌ **Game Phase** - Opening (moves 1-15), Middlegame (16-40), Endgame (40+) OR piece count

#### 4. Result Dimensions
- ✅ **Game Termination** - Already captured (Normal, Time forfeit, etc.)
- ✅ **Game Result** - Win/Loss/Draw

---

## Implementation Phases

### Phase 2: Move-Level Parsing (Next)
**Goal:** Extract move-by-move data without engine analysis

**Components:**
1. **Enhanced PGN Parser** (`enhanced_pgn_parser.py`)
   - Parse SAN move notation
   - Extract clock times per move
   - Detect castling (O-O, O-O-O)
   - Detect queen trades
   - Track material balance (simple piece values)
   - Detect game phases

2. **Move Dataset Schema** (CSV format)
   ```
   game_id, move_number, color, san_move, piece_moved, is_capture, is_check, 
   is_castle, castle_side, clock_time, time_spent, material_balance, 
   game_phase, queens_on_board
   ```

3. **Game Summary Dataset** (CSV format - enhanced from Phase 1)
   ```
   [All Phase 1 fields] + v7p3r_castling, opponent_castling, queen_traded_move, 
   avg_move_time_opening, avg_move_time_middlegame, avg_move_time_endgame,
   time_pressure_moves, opening_family
   ```

**Deliverables:**
- `extract_move_data.py` - Enhanced ETL for move-level analysis
- `v7p3r_moves_latest.csv` - Move-level dataset
- `v7p3r_game_summary_enhanced_latest.csv` - Enhanced game summary

---

### Phase 3: Multi-Dimensional Analytics Framework
**Goal:** Enable Lichess-style "slice X by Y" analysis

**Components:**
1. **Analytics Engine** (`insights_analytics.py`)
   - Flexible grouping/aggregation functions
   - Support for arbitrary dimension combinations
   - Statistical calculations (mean, median, percentiles)

2. **Insight Queries** (Examples)
   - Win rate by opponent strength + color
   - Average game length by opening family + time control
   - Queen trade frequency by game phase
   - Castling patterns by opponent ELO bracket
   - Time pressure impact on win rate
   - Material imbalance at decisive moments

3. **Interactive Report Generator** (`generate_insights_report.py`)
   - Pre-configured insight queries
   - Summary statistics
   - Trend analysis over time
   - Version comparison insights

**Deliverables:**
- `insights_analytics.py` - Core analytics framework
- `generate_insights_report.py` - Multi-dimensional reporting
- Example reports in `reports/insights/`

---

### Phase 4: Position Analysis (Advanced - Optional)
**Goal:** Add Stockfish-based accuracy and winning chances

**Requirements:**
- Stockfish binary
- Analysis scripts from `v7p3r-chess-engine/analytics/`
- Significant computation time (analyze 18k+ games)

**Components:**
1. **Position Analyzer** (`analyze_positions.py`)
   - Parse FEN positions per move
   - Run Stockfish evaluation
   - Calculate centipawn loss per move
   - Determine accuracy ratings
   - Identify blunders/mistakes/inaccuracies

2. **Enhanced Move Dataset**
   ```
   [Phase 2 fields] + stockfish_eval, best_move, centipawn_loss, 
   move_classification (blunder/mistake/inaccuracy/good/brilliant)
   ```

**Note:** This phase is optional and computationally expensive. Recommend completing Phases 2-3 first.

---

## Data Flow Architecture

```
┌─────────────────────┐
│  Raw PGN Files      │
│  (game_records/)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ETL Pipeline       │
│  - Phase 1: Headers │──────► v7p3r_game_data_latest.csv
│  - Phase 2: Moves   │──────► v7p3r_moves_latest.csv
│  - Phase 3: Stockfish│──────► v7p3r_positions_latest.csv
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Conformed Datasets │
│  (reporting_datasets/)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Analytics Engine   │
│  - Grouping/Agg     │
│  - Statistical Calc │
│  - Trend Analysis   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Reports & Insights │
│  (reports/)         │
└─────────────────────┘
```

---

## Quick Start (Next Steps)

### Step 1: Build Move Parser
```bash
cd reporting_scripts
python extract_move_data.py
```

### Step 2: Generate Insights
```bash
python generate_insights_report.py --dimension "opponent_strength" --metric "win_rate"
python generate_insights_report.py --dimension "opening_family,color" --metric "avg_game_length"
```

### Step 3: Explore Data
- Review `v7p3r_moves_latest.csv` for move-level patterns
- Check `reports/insights/` for multi-dimensional analysis

---

## Success Metrics

- ✅ **Phase 1 Complete:** 18,336 games extracted, basic reports generated
- ⏳ **Phase 2 Target:** Move-level data for all games + enhanced summaries
- ⏳ **Phase 3 Target:** 20+ pre-built insight queries, interactive slicing
- ⏳ **Phase 4 Target:** Accuracy analysis for priority games (100-500 games)

---

## Technical Notes

### Performance Considerations
- **Move parsing:** ~50-100 games/second (expect 3-5 minutes for full dataset)
- **Stockfish analysis:** ~10-30 seconds per game (6-12 hours for 1000 games)
- **Recommendation:** Start with Phase 2 (fast), defer Phase 4 for targeted analysis

### Data Quality
- **Missing clock data:** Some older PGN files may lack [%clk] annotations
- **Incomplete games:** Handle games with missing moves/termination
- **Version mapping:** Verify CHANGELOG dates align with actual deployments

### Extension Opportunities
- **Web dashboard:** Flask/Streamlit app for interactive insights
- **Real-time monitoring:** Websocket connection to Lichess API
- **Comparative analysis:** Benchmark against other bots/players
- **Machine learning:** Predict game outcomes based on early-game patterns

---

## References

- **Lichess Insights:** https://lichess.org/@/{username}/insights
- **PGN Specification:** https://www.chessclub.com/help/PGN-spec
- **Stockfish UCI Protocol:** https://www.chessprogramming.org/UCI
- **V7P3R Analytics:** `v7p3r-chess-engine/analytics/`

---

**Status:** Phase 1 Complete ✅ | Phase 2 Ready to Implement 🚀
