# JSON Analysis Source Data Contract

**Contract Version:** 1.0  
**Effective Date:** 2026-04-30  
**Status:** Active (Future Use - Stockfish Integration Phase)  
**Governed Data:** JSON analysis files uploaded to `gs://v7p3r-raw-data/analysis_results/`  
**Target Table:** `conformed_layer.analysis_results` (Future)

---

## 1. Contract Overview

### 1.1 Purpose

This contract defines the expected format and validation rules for Stockfish chess engine analysis results stored as JSON files.

**Scope:**
- All `.json` files in `gs://v7p3r-raw-data/analysis_results/`
- Move-by-move position evaluations
- Best move suggestions (principal variations)
- Centipawn loss calculations

**Out of Scope:**
- Non-Stockfish engine analysis (Leela, etc.)
- Tablebase lookups (endgame databases)
- Opening book references

### 1.2 Contract Status

**Current:** DRAFT - Stockfish integration not yet implemented  
**Target:** Phase 4 (Tier 2 Reporting Layer)  
**Dependencies:** Stockfish engine installation, analysis automation

---

## 2. Required JSON Fields

### 2.1 Top-Level Metadata

All JSON files must include these root-level fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `game_id` | STRING | Lichess game ID (PK/FK) | `"abc123xyz"` |
| `analysis_date` | STRING (ISO 8601) | When analysis was performed | `"2025-12-10T14:30:00Z"` |
| `engine_name` | STRING | Engine used | `"Stockfish 16"` |
| `engine_version` | STRING | Engine version number | `"16.0"` |
| `depth` | INTEGER | Analysis depth (plies) | `20` |
| `positions` | ARRAY | Array of position analyses | `[...]` |

**Validation Rules:**
- `game_id` must exist in `conformed_layer.game_records` (foreign key)
- `analysis_date` must be valid ISO 8601 timestamp
- `depth` must be 10-30 (reasonable analysis depth)
- `positions` array must have ≥1 element

### 2.2 Position Analysis Object

Each element in `positions` array must include:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `fen` | STRING | Position in FEN notation | `"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"` |
| `move_number` | INTEGER | Full move number | `1` (for 1. e4) |
| `ply` | INTEGER | Half-move number | `1` (White's 1st move) |
| `move_san` | STRING | Move in SAN notation | `"e4"` |
| `move_uci` | STRING | Move in UCI notation | `"e2e4"` |
| `score_cp` | INTEGER | Centipawn score (White POV) | `+35` |
| `score_mate` | INTEGER | Mate in N moves (NULL if not mate) | `3` or `NULL` |
| `best_move_uci` | STRING | Stockfish best move | `"e2e4"` |
| `pv_san` | ARRAY[STRING] | Principal variation (SAN) | `["e4", "e5", "Nf3"]` |
| `nodes` | INTEGER | Nodes searched | `1500000` |
| `time_ms` | INTEGER | Analysis time (milliseconds) | `2500` |

**Validation Rules:**
- `fen` must be valid FEN string
- `move_number` ≥ 1
- `ply` ≥ 1
- `score_cp` range: -2000 to +2000 (reasonable evaluation)
- `score_mate` and `score_cp` mutually exclusive (one must be NULL)
- `best_move_uci` must be valid UCI move
- `pv_san` array length 1-20 (reasonable PV depth)

---

## 3. Optional JSON Fields

### 3.1 Enhanced Metadata

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `multipv` | INTEGER | Multi-PV count (best N moves) | `3` |
| `hash_size_mb` | INTEGER | Hash table size used | `128` |
| `threads` | INTEGER | CPU threads used | `4` |
| `syzygy_enabled` | BOOLEAN | Tablebase lookup enabled | `true` |

**Behavior if Missing:**
- Defaults to single-PV analysis
- Hash size unknown (assume engine default)

### 3.2 Per-Position Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `nps` | INTEGER | Nodes per second | `600000` |
| `tbhits` | INTEGER | Tablebase hits | `0` |
| `depth_selective` | INTEGER | Selective search depth | `25` |
| `alternatives` | ARRAY[OBJECT] | Multi-PV alternatives | `[{"move": "d4", "score": 30}, ...]` |

---

## 4. JSON Schema

### 4.1 Example Valid JSON

```json
{
  "game_id": "abc123xyz",
  "analysis_date": "2025-12-10T14:30:00Z",
  "engine_name": "Stockfish 16",
  "engine_version": "16.0",
  "depth": 20,
  "multipv": 1,
  "hash_size_mb": 128,
  "threads": 4,
  "positions": [
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "move_number": 1,
      "ply": 1,
      "move_san": "e4",
      "move_uci": "e2e4",
      "score_cp": 35,
      "score_mate": null,
      "best_move_uci": "e2e4",
      "pv_san": ["e4", "e5", "Nf3", "Nc6", "Bb5"],
      "nodes": 1500000,
      "time_ms": 2500,
      "nps": 600000
    },
    {
      "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
      "move_number": 1,
      "ply": 2,
      "move_san": "e5",
      "move_uci": "e7e5",
      "score_cp": -25,
      "score_mate": null,
      "best_move_uci": "e7e5",
      "pv_san": ["e5", "Nf3", "Nc6", "Bb5", "a6"],
      "nodes": 1600000,
      "time_ms": 2600,
      "nps": 615384
    }
  ]
}
```

### 4.2 Minimal Valid JSON

```json
{
  "game_id": "xyz789",
  "analysis_date": "2025-12-10T15:00:00Z",
  "engine_name": "Stockfish 16",
  "engine_version": "16.0",
  "depth": 15,
  "positions": [
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "move_number": 1,
      "ply": 1,
      "move_san": "e4",
      "move_uci": "e2e4",
      "score_cp": 35,
      "score_mate": null,
      "best_move_uci": "e2e4",
      "pv_san": ["e4"],
      "nodes": 500000,
      "time_ms": 1000
    }
  ]
}
```

---

## 5. Calculated Metrics

### 5.1 Centipawn Loss (CPL)

**Formula:**
```
CPL = |score_after_move - score_before_move|
```

**Interpretation:**
- CPL = 0-25: Excellent move
- CPL = 26-50: Inaccuracy
- CPL = 51-100: Mistake
- CPL = 101-200: Blunder
- CPL > 200: Severe blunder

**Storage:** Calculated during ETL, stored in Tier 2 reporting tables

### 5.2 Move Quality Classification

**Categories:**
- `best`: move_uci == best_move_uci
- `good`: CPL ≤ 25
- `inaccurate`: CPL 26-50
- `mistake`: CPL 51-100
- `blunder`: CPL > 100

### 5.3 Position Complexity

**Heuristics:**
- Node count (higher = more complex)
- PV length (shorter PV = more forced position)
- Score stability (score variance across depths)

---

## 6. Validation Rules

### 6.1 JSON Schema Validation

**Check Sequence:**
1. Verify JSON is valid (parseable)
2. Verify required top-level fields present
3. Verify `game_id` exists in `game_records` (FK)
4. Verify `positions` array not empty
5. For each position: Verify required fields present
6. Validate FEN syntax
7. Validate score ranges (-2000 to +2000 centipawns)

**Failure Action:**
- Log error to `operational_events`
- Reject entire JSON file (all-or-nothing)
- Move file to `gs://v7p3r-raw-data/invalid/`

### 6.2 FEN Validation

**Format:** 6 space-separated components
```
<pieces> <active_color> <castling> <en_passant> <halfmove_clock> <fullmove_number>
```

**Example:**
```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

**Validation:**
- Pieces: 8 ranks, `/` separators, valid piece letters (pPnNbBrRqQkK)
- Active color: `w` or `b`
- Castling: `KQkq`, `-`, or subset (e.g., `Kq`)
- En passant: Square (e.g., `e3`) or `-`
- Halfmove clock: Integer 0-100
- Fullmove number: Integer ≥ 1

---

## 7. Expansion Rules

### 7.1 Allowed Expansions

**New Optional Fields:**
- New engine parameters (hash size, threads, etc.)
- New analysis modes (Multi-PV, syzygy, etc.)
- New per-position metrics (NPS, TBhits, selective depth)

**Schema Evolution:**
- New NULLABLE fields added to `analysis_results` table
- Ingestion script updated to extract new fields
- Historical analyses backfilled with NULL for new fields

### 7.2 Breaking Changes

**Forbidden:**
- Changing `game_id` format (must remain Lichess ID)
- Changing `fen` to different position notation
- Removing required fields (fen, move_san, score_cp, etc.)

**Procedure for Breaking Changes:**
- Same as PGN contract (version increment, dual-format support, migration)

---

## 8. Integration with Conformed Layer

### 8.1 Target Schema (Future)

```sql
CREATE TABLE conformed_layer.analysis_results (
  game_id STRING NOT NULL,           -- FK to game_records
  ply INTEGER NOT NULL,              -- Half-move number
  fen STRING NOT NULL,               -- Position FEN
  move_san STRING NOT NULL,          -- Move played (SAN)
  move_uci STRING NOT NULL,          -- Move played (UCI)
  score_cp INTEGER,                  -- Centipawn evaluation
  score_mate INTEGER,                -- Mate in N (NULL if not mate)
  best_move_uci STRING NOT NULL,     -- Stockfish best move
  pv_san ARRAY<STRING>,              -- Principal variation
  nodes INTEGER,                     -- Nodes searched
  time_ms INTEGER,                   -- Analysis time
  centipawn_loss INTEGER,            -- Calculated CPL
  move_quality STRING,               -- 'best', 'good', 'inaccurate', 'mistake', 'blunder'
  analysis_date TIMESTAMP,           -- When analysis performed
  engine_version STRING,             -- Stockfish version
  ingested_at TIMESTAMP,
  PRIMARY KEY (game_id, ply)
);
```

### 8.2 ETL Logic

**Ingestion Steps:**
1. Parse JSON file
2. Validate against contract
3. For each position in `positions` array:
   - Calculate centipawn loss (compare to previous position)
   - Classify move quality (best/good/inaccurate/mistake/blunder)
   - Insert row to `analysis_results` table
4. Update `operational_events` with ingestion status

---

## 9. Examples

### 9.1 Mate Score Example

```json
{
  "game_id": "mate_example",
  "analysis_date": "2025-12-10T16:00:00Z",
  "engine_name": "Stockfish 16",
  "engine_version": "16.0",
  "depth": 20,
  "positions": [
    {
      "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
      "move_number": 4,
      "ply": 7,
      "move_san": "Qxf7#",
      "move_uci": "h5f7",
      "score_cp": null,
      "score_mate": 1,
      "best_move_uci": "h5f7",
      "pv_san": ["Qxf7#"],
      "nodes": 250000,
      "time_ms": 500
    }
  ]
}
```

### 9.2 Multi-PV Example

```json
{
  "game_id": "multipv_example",
  "analysis_date": "2025-12-10T17:00:00Z",
  "engine_name": "Stockfish 16",
  "engine_version": "16.0",
  "depth": 20,
  "multipv": 3,
  "positions": [
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "move_number": 1,
      "ply": 1,
      "move_san": "e4",
      "move_uci": "e2e4",
      "score_cp": 35,
      "score_mate": null,
      "best_move_uci": "e2e4",
      "pv_san": ["e4", "e5", "Nf3"],
      "nodes": 1500000,
      "time_ms": 2500,
      "alternatives": [
        {"move_uci": "d2d4", "score_cp": 32, "pv_san": ["d4", "d5", "c4"]},
        {"move_uci": "c2c4", "score_cp": 28, "pv_san": ["c4", "e5", "Nc3"]}
      ]
    }
  ]
}
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-30 | Initial contract (draft for Phase 4) | V7P3R Analytics Team |

---

## 11. References

**UCI Protocol:**
- Universal Chess Interface specification
- Stockfish documentation: https://stockfishchess.org/

**FEN Notation:**
- Forsyth-Edwards Notation standard
- Wikipedia: https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation

**Related Contracts:**
- `pgn_game_source_contract.md` - PGN game files
- `changelog_version_source_contract.md` - Engine version mapping

---

**Contract Owner:** V7P3R Analytics Team  
**Last Updated:** 2026-04-30  
**Next Review:** Phase 4 (Stockfish Integration)
