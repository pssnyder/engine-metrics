# PGN Game Source Data Contract

**Contract Version:** 1.0  
**Effective Date:** 2026-04-30  
**Status:** Active  
**Governed Data:** PGN game files uploaded to `gs://v7p3r-raw-data/game_records/`  
**Target Table:** `conformed_layer.game_records`

---

## 1. Contract Overview

### 1.1 Purpose

This contract defines the expected format and validation rules for PGN (Portable Game Notation) game files ingested into the V7P3R Analytics platform.

**Scope:**
- All `.pgn` files uploaded to `gs://v7p3r-raw-data/game_records/`
- All PGN files in `gs://v7p3r-raw-data/v7p3r_docs/` subdirectories
- Multi-game PGN files (concatenated games)

**Out of Scope:**
- Non-PGN game formats (FEN, EPD, etc.)
- Incomplete or corrupted PGN files

### 1.2 Contract Guarantees

**If this contract is satisfied:**
- Ingestion script will successfully parse and load game data
- All required fields will be populated in `game_records` table
- Foreign key relationships will be validated
- Game integrity guaranteed (move sequences valid)

**If this contract is violated:**
- Ingestion may fail with error logged to `operational_events`
- File moved to `gs://v7p3r-raw-data/invalid/` for manual review
- No partial data inserted (transactional ingestion)

---

## 2. Required PGN Headers

### 2.1 Mandatory Headers (MUST be present)

All PGN files must include these Seven Tag Roster (STR) headers:

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `Event` | STRING | Game event or match type | `"Rated Bullet game"` |
| `Site` | STRING | Platform or location URL | `"https://lichess.org/abc123"` |
| `Date` | DATE | Game date (YYYY.MM.DD) | `"2025.12.10"` |
| `Round` | STRING | Round number or identifier | `"?"` (if not tournament) |
| `White` | STRING | White player username | `"v7p3r_bot"` |
| `Black` | STRING | Black player username | `"opponent123"` |
| `Result` | STRING | Game outcome | `"1-0"`, `"0-1"`, `"1/2-1/2"`, `"*"` |

**Validation Rules:**
- All headers must be present (even if value is `"?"`)
- Header format: `[HeaderName "HeaderValue"]`
- One header per line
- Headers must appear before move text

### 2.2 Move Text (REQUIRED)

**Format:** Standard Algebraic Notation (SAN)  
**Example:**
```
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7
```

**Validation Rules:**
- At least 1 move (ply) required
- Moves must be valid chess notation
- Move numbers optional but recommended
- Comments allowed in `{ }` braces
- Variations allowed in `( )` parentheses

---

## 3. Optional PGN Headers

### 3.1 Recommended Headers

These headers greatly improve analytics quality:

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `WhiteElo` | INTEGER | White player ELO rating | `"1650"` |
| `BlackElo` | INTEGER | Black player ELO rating | `"1720"` |
| `TimeControl` | STRING | Time control format | `"60+0"` (60 sec, no increment) |
| `ECO` | STRING | Opening classification code | `"C50"` |
| `Opening` | STRING | Full opening name | `"Italian Game: Giuoco Pianissimo"` |
| `Termination` | STRING | How game ended | `"Normal"`, `"Time forfeit"`, `"Resignation"` |

**Behavior if Missing:**
- `WhiteElo` / `BlackElo`: NULL in database, impacts opponent strength analysis
- `TimeControl`: NULL, cannot categorize as bullet/blitz/rapid
- `ECO` / `Opening`: NULL, opening analysis limited
- `Termination`: NULL, cannot detect time forfeit rate

### 3.2 V7P3R-Specific Headers (Optional)

Custom headers used by V7P3R bot for enhanced analytics:

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `EngineVersion` | STRING | V7P3R version used | `"v17.1"` |
| `WhiteRatingDiff` | STRING | ELO change for White | `"+5"` |
| `BlackRatingDiff` | STRING | ELO change for Black | `"-5"` |
| `WhiteTitle` | STRING | White player title | `"BOT"`, `"GM"`, `"IM"` |
| `BlackTitle` | STRING | Black player title | `"BOT"`, `"GM"`, `"IM"` |

**Behavior if Missing:**
- `EngineVersion`: Derived from filename or date mapping (CHANGELOG.md)
- `RatingDiff`: NULL, cannot track ELO progression
- `Title`: NULL, cannot filter bot-vs-human games

---

## 4. Data Type Specifications

### 4.1 Date Format

**Standard:** PGN date format `YYYY.MM.DD`  
**Examples:**
- `2025.12.10` (December 10, 2025)
- `2025.12.??` (Unknown day, valid)
- `2025.??.??` (Unknown month/day, valid)

**Validation:**
- Year: 2000-2099 (reasonable range for chess games)
- Month: 01-12 or `??`
- Day: 01-31 or `??`

**Conversion to BigQuery:**
- Full date `2025.12.10` → DATE `2025-12-10`
- Partial date `2025.12.??` → DATE `2025-12-01` (first of month)
- Unknown date `????.??.??` → NULL

### 4.2 Time Control Format

**Standard:** `{initial}+{increment}` (seconds)  
**Examples:**
- `60+0` = 1 minute bullet, no increment
- `180+2` = 3 minute blitz, 2 second increment
- `600+0` = 10 minute rapid, no increment
- `1800+30` = 30 minute classical, 30 second increment
- `-` = Unlimited (correspondence)

**Validation:**
- Initial: 0-10800 seconds (0-3 hours)
- Increment: 0-60 seconds
- Format: `\d+\+\d+` regex or `-`

### 4.3 Result Format

**Standard:** Chess result notation  
**Valid Values:**
- `1-0` = White wins
- `0-1` = Black wins
- `1/2-1/2` = Draw
- `*` = Game in progress or unknown

**Validation:**
- Must be one of the 4 valid values
- Case-sensitive

### 4.4 ELO Format

**Standard:** Integer rating (Elo scale)  
**Valid Range:** 500-3000  
**Examples:**
- `1650` = Average club player
- `2200` = National master
- `2700` = Super grandmaster
- `?` = Unknown (converted to NULL)

**Validation:**
- Must be integer or `?`
- If integer, must be 500-3000 (human-reachable range)

---

## 5. Move Text Specifications

### 5.1 Standard Algebraic Notation (SAN)

**Piece Notation:**
- `K` = King
- `Q` = Queen
- `R` = Rook
- `B` = Bishop
- `N` = Knight
- Pawn moves have no prefix (e.g., `e4`)

**Special Moves:**
- `O-O` = Kingside castle
- `O-O-O` = Queenside castle
- `e8=Q` = Pawn promotion to Queen
- `Nxe5` = Knight captures on e5
- `exd6 e.p.` = En passant capture

**Check and Mate:**
- `+` = Check
- `#` = Checkmate

**Examples:**
```
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6
```

### 5.2 Annotations (Allowed)

**Comments:** `{ This is a comment }`  
**Variations:** `( 5... Nxe4 6. d4 d5 )`  
**Numeric Annotation Glyphs (NAGs):** `$1` (good move), `$2` (mistake), etc.

**Parsing Behavior:**
- Comments ignored during ingestion (not stored)
- Variations ignored (only mainline stored)
- NAGs ignored

---

## 6. File Format Specifications

### 6.1 File Structure

**Single-Game PGN:**
```
[Event "Rated Bullet game"]
[Site "https://lichess.org/abc123"]
[Date "2025.12.10"]
[Round "?"]
[White "v7p3r_bot"]
[Black "opponent123"]
[Result "1-0"]
[WhiteElo "1650"]
[BlackElo "1720"]
[TimeControl "60+0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0
```

**Multi-Game PGN (Concatenated):**
```
[Event "Rated Bullet game"]
...
1. e4 e5 ... 1-0

[Event "Rated Blitz game"]
...
1. d4 d5 ... 0-1
```

**Separator:** Blank line between games

### 6.2 Character Encoding

**Standard:** UTF-8  
**Alternative:** ASCII (subset of UTF-8)

**Invalid Encodings:**
- UTF-16, Latin-1, Windows-1252 (reject file)

### 6.3 Line Endings

**Accepted:**
- Unix: `\n` (LF)
- Windows: `\r\n` (CRLF)
- Mac Classic: `\r` (CR)

**Normalization:** Ingestion script handles all formats

### 6.4 File Size Limits

**Recommended:** <10 MB per file  
**Maximum:** 100 MB per file  
**Reason:** Large files increase ingestion time and memory usage

**Best Practice:** Split large PGN files into chunks of 1000-5000 games

---

## 7. Validation Rules

### 7.1 Header Validation

**Check Sequence:**
1. Verify all 7 required headers present (Event, Site, Date, Round, White, Black, Result)
2. Validate Date format `YYYY.MM.DD`
3. Validate Result is one of: `1-0`, `0-1`, `1/2-1/2`, `*`
4. If WhiteElo/BlackElo present, validate 500-3000 range
5. If TimeControl present, validate format `\d+\+\d+` or `-`

**Failure Action:**
- Log error to `operational_events` table
- Skip game (continue to next game in file)
- If >50% games in file fail: Reject entire file

### 7.2 Move Text Validation

**Check Sequence:**
1. Verify at least 1 move present
2. Parse SAN notation (basic syntax check)
3. Optional: Validate move legality (chess rules) - deferred for performance

**Failure Action:**
- Log error with game ID
- Skip game (continue to next game)

### 7.3 Foreign Key Validation

**V7P3R Game Detection:**
- Check if White or Black player is `v7p3r_bot`
- If yes: Extract opponent name, opponent ELO
- Derive engine version from:
  1. `EngineVersion` header (if present)
  2. Filename pattern `v7p3r_v17.1_games.pgn`
  3. Date mapping via CHANGELOG.md

**Foreign Key Check:**
- If engine_version extracted: Validate exists in `conformed_layer.engine_versions`
- If not exists: Log warning, allow NULL (version mapping may be incomplete)

---

## 8. Expansion Rules

### 8.1 Allowed Expansions (Non-Breaking)

**New Optional Headers:**
- Any new PGN header can be added
- Ingestion script dynamically adds new columns to BigQuery schema
- Example: Adding `Variant` header for Chess960 games

**New Annotations:**
- New comment formats allowed (ignored by parser)
- New NAG codes allowed (ignored by parser)

**Schema Evolution:**
- New NULLABLE fields added to `game_records` table
- Historical games backfilled with NULL for new fields

### 8.2 Breaking Changes (REQUIRES CONTRACT UPDATE)

**Forbidden Changes:**
- Removing required headers (Event, Site, Date, etc.)
- Changing Result format (e.g., using `W` instead of `1-0`)
- Changing Date format (e.g., `YYYY-MM-DD` instead of `YYYY.MM.DD`)
- Changing move notation from SAN to UCI or other format

**Procedure for Breaking Changes:**
1. Propose change in contract review
2. Update ingestion script to handle both old and new formats
3. Increment contract version (v1.0 → v2.0)
4. Document migration path
5. Deploy updated ingestion script
6. Test with historical and new data

---

## 9. Examples

### 9.1 Valid PGN (Minimal)

```
[Event "Casual game"]
[Site "https://lichess.org/abc123"]
[Date "2025.12.10"]
[Round "?"]
[White "v7p3r_bot"]
[Black "opponent123"]
[Result "1-0"]

1. e4 e5 2. Nf3 1-0
```

**Result:** ✅ PASS - All required headers present, valid move text

### 9.2 Valid PGN (Enhanced)

```
[Event "Rated Bullet game"]
[Site "https://lichess.org/xyz789"]
[Date "2025.12.10"]
[Round "?"]
[White "v7p3r_bot"]
[Black "opponent123"]
[Result "1-0"]
[WhiteElo "1650"]
[BlackElo "1720"]
[WhiteRatingDiff "+5"]
[BlackRatingDiff "-5"]
[WhiteTitle "BOT"]
[TimeControl "60+0"]
[ECO "C50"]
[Opening "Italian Game: Giuoco Pianissimo"]
[Termination "Normal"]
[EngineVersion "v17.1"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. d3 Nf6 5. Nc3 d6 6. Bg5 h6 7. Bh4 g5 8. Bg3 h5
9. h3 Qe7 10. Nxg5 Rg8 11. Nf3 Nh7 12. Nh4 Nf6 13. Nf5 Bxf5 14. exf5 O-O-O 
15. O-O Rdg8 16. Nd5 Nxd5 17. Bxd5 f6 18. c3 Qf7 19. Qa4 Kb8 20. Rfe1 Ne7 
21. Bxb7 Kxb7 22. Qb5+ Kc8 23. Qa6+ Kb8 24. Rab1 Qxf5 25. Qb5+ Kc8 26. Qa6+ Kb8 
27. Rxb7+ Kxb7 28. Rb1# 1-0
```

**Result:** ✅ PASS - All headers present, rich metadata, valid chess notation

### 9.3 Invalid PGN (Missing Required Header)

```
[Event "Rated game"]
[Site "https://lichess.org/bad123"]
[White "v7p3r_bot"]
[Black "opponent456"]
[Result "1-0"]

1. e4 e5 2. Nf3 1-0
```

**Result:** ❌ FAIL - Missing required headers: `Date`, `Round`  
**Action:** Skip game, log error

### 9.4 Invalid PGN (Bad Date Format)

```
[Event "Casual game"]
[Site "https://lichess.org/bad456"]
[Date "2025-12-10"]
[Round "?"]
[White "v7p3r_bot"]
[Black "opponent789"]
[Result "1-0"]

1. e4 1-0
```

**Result:** ❌ FAIL - Date format should be `2025.12.10` not `2025-12-10`  
**Action:** Attempt to parse and convert, log warning if fails

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-30 | Initial contract created | V7P3R Analytics Team |

---

## 11. References

**PGN Specification:**
- Official PGN Standard: http://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm
- PGN Supplement (Additions): http://www.enpassant.dk/chess/palview/enhancedpgn.htm

**Related Contracts:**
- `json_analysis_source_contract.md` - Stockfish analysis JSON
- `changelog_version_source_contract.md` - Engine version mapping

**Governed Resources:**
- Ingestion Script: `scripts/ingestion/05_ingest_game_records.py`
- Target Table: `conformed_layer.game_records`
- Source Bucket: `gs://v7p3r-raw-data/game_records/`

---

**Contract Owner:** V7P3R Analytics Team  
**Last Updated:** 2026-04-30  
**Next Review:** Quarterly (July 2026)
