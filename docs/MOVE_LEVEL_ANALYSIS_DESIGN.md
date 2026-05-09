# Move-Level Analysis Design

## Purpose
Deep-dive analysis of individual moves to identify:
- **Tactical accuracy** per engine version
- **Positional strengths/weaknesses** by board state
- **Move quality distribution** (brilliant/good/inaccuracy/blunder)
- **Opening/middlegame/endgame performance** patterns

## Current State: `moves` Table Schema

From `terraform/bigquery_moves.tf`:
- **game_id**: STRING (FK to game_data)
- **ply**: INTEGER (half-move number, 1-indexed)
- **move**: STRING (SAN notation, e.g., "Nf3", "e4")
- **fen_before**: STRING (position before move)
- **fen_after**: STRING (position after move)
- **comment**: STRING (engine commentary if available)
- **ingested_at**: TIMESTAMP

**Current Record Count**: 1,350,163 rows (from 5,069 unique games = avg 266 moves/game)

## Proposed Enhancement: `moves_analyzed` Table

### Core Move Data (from existing `moves` table)
```sql
game_id              STRING      -- Link to game_data.game_id
ply                  INTEGER     -- Half-move number (1=White's first move, 2=Black's first move)
move_san             STRING      -- Move in Standard Algebraic Notation (e.g., "Nf3")
fen_before           STRING      -- Position before this move (for analysis)
fen_after            STRING      -- Position after this move
```

### Player Context (JOIN from game_data)
```sql
engine_version       STRING      -- Which v7p3r version played this move
player_side          STRING      -- 'white' or 'black'
opponent             STRING      -- Opponent username
game_type            STRING      -- 'lichess_rated', 'lichess_casual', 'tournament'
time_control         STRING      -- Game time control (e.g., "300+4")
```

### Position Context
```sql
game_phase           STRING      -- 'opening' (ply 1-20), 'middlegame' (ply 21-60), 'endgame' (ply 61+)
piece_count          INTEGER     -- Total pieces on board (for endgame detection)
material_balance     INTEGER     -- Centipawns material advantage for side to move
castling_status      STRING      -- e.g., "both_castled", "white_only", "neither"
```

### Engine Evaluation (from PGN comments or Stockfish analysis)
```sql
engine_eval_cp       INTEGER     -- Centipawn evaluation from engine perspective
                                  -- Positive = advantage, negative = disadvantage
                                  -- NULL if not available in PGN
engine_eval_mate     INTEGER     -- Mate in N moves (NULL if not mate)
engine_depth         INTEGER     -- Search depth for this evaluation
engine_name          STRING      -- Which engine provided eval (e.g., "v18.0", "Stockfish 16")
```

### Post-Game Analysis (Stockfish 16+ analysis)
```sql
best_move_san        STRING      -- Best move according to Stockfish analysis
best_move_eval_cp    INTEGER     -- Eval after best move
played_move_eval_cp  INTEGER     -- Eval after the move that was actually played
eval_loss_cp         INTEGER     -- best_move_eval_cp - played_move_eval_cp (centipawn loss)
```

### Move Quality Classification
```sql
move_quality         STRING      -- Classification based on eval_loss_cp:
                                  -- 'brilliant' (eval_loss_cp <= -20, sacrifices or complex)
                                  -- 'great' (eval_loss_cp <= -10)
                                  -- 'good' (eval_loss_cp <= 0)
                                  -- 'inaccuracy' (eval_loss_cp 1-100)
                                  -- 'mistake' (eval_loss_cp 101-300)
                                  -- 'blunder' (eval_loss_cp > 300)
                                  -- 'forced' (only legal move)
is_tactical          BOOLEAN     -- Move involves capture, check, or threat
is_book_move         BOOLEAN     -- Move is in opening book (first 10 moves matching ECO)
is_only_legal_move   BOOLEAN     -- Only one legal move available
```

### Move Themes (Advanced)
```sql
move_themes          ARRAY<STRING>  -- Tags like ['fork', 'pin', 'discovered_attack', 'sacrifice']
creates_threat       BOOLEAN        -- Move creates immediate tactical threat
defends_threat       BOOLEAN        -- Move defends against opponent's threat
positional_gain      STRING         -- 'space', 'development', 'king_safety', 'pawn_structure', NULL
```

## ETL Pipeline Design

### Phase 1: Extract Move Data with Player Context
**Input**: `moves` (1.35M rows) + `game_data` (5,069 games)  
**Output**: `moves_with_context` (1.35M rows)

```sql
CREATE TABLE moves_with_context AS
SELECT
  m.game_id,
  m.ply,
  m.move AS move_san,
  m.fen_before,
  m.fen_after,
  m.comment,
  
  -- Join game context
  g.engine_version,
  g.opponent,
  g.game_type,
  g.time_control,
  g.eco,
  g.opening,
  
  -- Determine which side v7p3r played this move
  CASE
    WHEN MOD(m.ply, 2) = 1 AND g.color = 'white' THEN TRUE   -- Odd ply, v7p3r is white
    WHEN MOD(m.ply, 2) = 0 AND g.color = 'black' THEN TRUE   -- Even ply, v7p3r is black
    ELSE FALSE
  END AS is_v7p3r_move,
  
  CASE
    WHEN MOD(m.ply, 2) = 1 THEN 'white'
    ELSE 'black'
  END AS player_side,
  
  -- Game phase classification
  CASE
    WHEN m.ply <= 20 THEN 'opening'
    WHEN m.ply <= 60 THEN 'middlegame'
    ELSE 'endgame'
  END AS game_phase
  
FROM conformed_layer.moves m
JOIN conformed_layer.game_data g ON m.game_id = g.game_id
WHERE g.is_v7p3r_elo_reliable = TRUE  -- Only analyze games with reliable data
```

**Filters**:
- Only games with reliable ELO (excludes local Arena tests)
- Only moves by v7p3r engines (exclude opponent moves for now)

**Result**: ~675k v7p3r moves (assuming ~50% of 1.35M total moves)

### Phase 2: Parse Engine Evaluations from Comments
**Input**: `moves_with_context.comment` field  
**Output**: `moves_with_evals`

Many PGN files include engine evaluations in comments like:
- `{ +0.45/12 }` = +45 centipawns at depth 12
- `{ -1.23 }` = -123 centipawns
- `{ #3 }` = Mate in 3

**Python script to parse**:
```python
def parse_eval_comment(comment):
    """Parse engine eval from PGN comment."""
    if not comment:
        return None, None, None
    
    # Match patterns like "+0.45/12" or "-1.23" or "#3"
    import re
    
    # Centipawn eval with optional depth
    cp_match = re.search(r'([+-]?\d+\.\d+)(?:/(\d+))?', comment)
    if cp_match:
        cp = int(float(cp_match.group(1)) * 100)  # Convert to centipawns
        depth = int(cp_match.group(2)) if cp_match.group(2) else None
        return cp, None, depth
    
    # Mate eval
    mate_match = re.search(r'#([+-]?\d+)', comment)
    if mate_match:
        mate = int(mate_match.group(1))
        return None, mate, None
    
    return None, None, None
```

### Phase 3: Stockfish Analysis (Batch Processing)
**Input**: Unique FEN positions from `moves_with_context.fen_before`  
**Output**: `position_analysis` table with best moves

This is **computationally expensive** - need to analyze ~675k unique positions.

**Options**:
1. **Use existing analysis** if PGN already has engine evals
2. **Batch Stockfish analysis** (run overnight, ~1-2 positions/second = ~8-16 hours)
3. **Sample approach** (analyze only critical positions: opening variations, tactical positions)

**Recommended**: Start with existing PGN evals, add Stockfish analysis for positions without evals

**Stockfish Analysis Script**:
```python
import chess
import chess.engine

def analyze_position(fen, time_limit=0.1):
    """Analyze position with Stockfish."""
    board = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci("stockfish") as engine:
        info = engine.analyse(board, chess.engine.Limit(time=time_limit))
        
        best_move = info['pv'][0]
        eval_cp = info['score'].relative.cp  # Centipawns
        eval_mate = info['score'].relative.mate  # Mate in N
        
        return {
            'best_move_uci': best_move.uci(),
            'best_move_san': board.san(best_move),
            'eval_cp': eval_cp,
            'eval_mate': eval_mate
        }
```

### Phase 4: Move Quality Classification
**Input**: `moves_with_evals` + Stockfish `position_analysis`  
**Output**: Final `moves_analyzed` table

```sql
CREATE TABLE moves_analyzed AS
SELECT
  m.*,
  pa.best_move_san,
  pa.best_move_eval_cp,
  
  -- Calculate eval loss
  COALESCE(m.engine_eval_cp, 0) - COALESCE(pa.best_move_eval_cp, 0) AS eval_loss_cp,
  
  -- Classify move quality
  CASE
    WHEN m.move_san = pa.best_move_san THEN 'best'
    WHEN COALESCE(m.engine_eval_cp, 0) - COALESCE(pa.best_move_eval_cp, 0) <= -20 THEN 'brilliant'
    WHEN COALESCE(m.engine_eval_cp, 0) - COALESCE(pa.best_move_eval_cp, 0) <= 0 THEN 'good'
    WHEN COALESCE(m.engine_eval_cp, 0) - COALESCE(pa.best_move_eval_cp, 0) <= 100 THEN 'inaccuracy'
    WHEN COALESCE(m.engine_eval_cp, 0) - COALESCE(pa.best_move_eval_cp, 0) <= 300 THEN 'mistake'
    ELSE 'blunder'
  END AS move_quality

FROM moves_with_context m
LEFT JOIN position_analysis pa ON m.fen_before = pa.fen
```

## Analysis Queries Enabled

### 1. Move Quality by Engine Version
```sql
SELECT
  engine_version,
  COUNT(*) as total_moves,
  COUNTIF(move_quality = 'best') as best_moves,
  COUNTIF(move_quality = 'good') as good_moves,
  COUNTIF(move_quality = 'inaccuracy') as inaccuracies,
  COUNTIF(move_quality = 'mistake') as mistakes,
  COUNTIF(move_quality = 'blunder') as blunders,
  ROUND(AVG(eval_loss_cp), 1) as avg_centipawn_loss
FROM moves_analyzed
WHERE is_v7p3r_move = TRUE
GROUP BY engine_version
ORDER BY avg_centipawn_loss ASC
```

### 2. Tactical Accuracy by Game Phase
```sql
SELECT
  engine_version,
  game_phase,
  ROUND(AVG(eval_loss_cp), 1) as avg_cp_loss,
  COUNTIF(move_quality IN ('mistake', 'blunder')) as errors
FROM moves_analyzed
WHERE is_v7p3r_move = TRUE AND is_tactical = TRUE
GROUP BY engine_version, game_phase
```

### 3. Opening Repertoire Analysis
```sql
SELECT
  engine_version,
  eco,
  opening,
  COUNT(DISTINCT game_id) as games_played,
  ROUND(AVG(CASE WHEN is_book_move THEN eval_loss_cp END), 1) as opening_accuracy
FROM moves_analyzed
WHERE game_phase = 'opening' AND is_v7p3r_move = TRUE
GROUP BY engine_version, eco, opening
HAVING games_played >= 5
ORDER BY opening_accuracy ASC
```

### 4. Endgame Conversion Accuracy
```sql
SELECT
  engine_version,
  COUNTIF(game_phase = 'endgame' AND move_quality = 'best') as precise_endgame_moves,
  COUNTIF(game_phase = 'endgame') as total_endgame_moves,
  ROUND(COUNTIF(game_phase = 'endgame' AND move_quality = 'best') * 100.0 / COUNTIF(game_phase = 'endgame'), 1) as endgame_precision_pct
FROM moves_analyzed
WHERE is_v7p3r_move = TRUE
GROUP BY engine_version
```

## Implementation Plan

### Immediate (Phase 1)
1. ✅ Analyze current `moves` table schema
2. ✅ Design `moves_analyzed` schema
3. ⏳ Check PGN files for existing engine evaluations
4. ⏳ Create `moves_with_context` table (JOIN moves + game_data)

### Short-term (Phase 2)
5. Parse engine evals from PGN comments (if available)
6. Determine % of moves with existing evaluations
7. Decide: Full Stockfish analysis vs sample-based analysis

### Medium-term (Phase 3)
8. Run Stockfish batch analysis for positions without evals
9. Create `position_analysis` lookup table
10. Join with moves to create final `moves_analyzed`

### Long-term (Phase 4)
11. Build move quality classification logic
12. Add tactical theme detection (forks, pins, etc.)
13. Create reporting views for move-level insights

## Success Criteria

1. **Coverage**: ≥90% of v7p3r moves have quality classification
2. **Accuracy**: Move quality aligns with chess.com/lichess analysis
3. **Performance**: Queries on 675k+ moves run in <10 seconds
4. **Insights**: Can identify specific weaknesses per engine version (e.g., "v17.4 blunders in complex middlegames")

## Next Steps

**Question for User**:
1. Do PGN files already contain engine evaluations in comments?
2. Preference: Full Stockfish analysis (8-16 hours) or sample-based (2-3 hours)?
3. Should we analyze opponent moves too, or focus only on v7p3r moves?

---

**Ready to proceed with Phase 1 when approved.**
