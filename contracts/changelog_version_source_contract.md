# CHANGELOG Version Source Data Contract

**Contract Version:** 1.0  
**Effective Date:** 2026-04-30  
**Status:** Active  
**Governed Data:** `CHANGELOG.md` file in V7P3R engine repository  
**Target Table:** `conformed_layer.engine_versions`

---

## 1. Contract Overview

### 1.1 Purpose

This contract defines the expected format and validation rules for the CHANGELOG.md file that maps V7P3R engine version numbers to deployment dates and descriptions.

**Scope:**
- `CHANGELOG.md` file in V7P3R engine repo (`v7p3r-chess-engine/`)
- Version number to date mapping
- Version descriptions and change summaries

**Out of Scope:**
- Detailed code changes (tracked in git commits)
- Performance benchmarks (tracked in `deployment_log.json`)
- Testing results

### 1.2 Contract Guarantees

**If this contract is satisfied:**
- Engine version can be derived from game date
- Version lineage correctly tracked (v14.1 → v17.0 → v17.1, etc.)
- Game records can be filtered by version

**If this contract is violated:**
- Version mapping may fail (games assigned NULL version)
- Temporal analysis by version impossible
- Upgrade recommendations inaccurate

---

## 2. Required CHANGELOG Format

### 2.1 Markdown Structure

**Standard:** Keep a Changelog format (https://keepachangelog.com/)  
**Example:**
```markdown
# Changelog

All notable changes to V7P3R Chess Engine will be documented in this file.

## [17.1.0] - 2025-12-10

### Added
- Bishop pair bonus (+30cp when both bishops present)
- Isolated pawn penalty (-15cp per isolated pawn)

### Changed
- Lowered repetition threshold from 200cp to 50cp

### Fixed
- Fix PV instant move causing time forfeit

## [17.0.0] - 2025-12-05

### Added
- Time manager integration for better clock management
- Mate-in-1 fast path detection

### Performance
- 38% speedup in pure endgames by skipping PST
```

### 2.2 Required Components

**Each version entry must include:**

1. **Version Header:** `## [X.Y.Z] - YYYY-MM-DD`
   - Version number: Semantic versioning (MAJOR.MINOR.PATCH)
   - Release date: ISO date format (YYYY-MM-DD)

2. **Change Categories (at least one):**
   - `### Added` - New features
   - `### Changed` - Modifications to existing features
   - `### Fixed` - Bug fixes
   - `### Removed` - Removed features
   - `### Performance` - Performance improvements
   - `### Deprecated` - Soon-to-be-removed features

3. **Change Descriptions:**
   - Bullet points under each category
   - Concise description (1-2 lines)
   - Quantified when possible (+30cp, 38% speedup)

### 2.3 Version Number Format

**Standard:** Semantic Versioning (https://semver.org/)  
**Format:** `MAJOR.MINOR.PATCH`

**Examples:**
- `14.1.0` - Major version 14, minor version 1, patch 0
- `17.0.0` - Major version 17 (breaking change from v16.x)
- `17.1.2` - Patch version 2 for v17.1

**Validation:**
- Version must be `\d+\.\d+\.\d+` regex
- Major, minor, patch must be non-negative integers
- Version numbers strictly increasing over time

### 2.4 Release Date Format

**Standard:** ISO 8601 date format `YYYY-MM-DD`  
**Examples:**
- `2025-12-10` (December 10, 2025)
- `2025-01-05` (January 5, 2025)

**Validation:**
- Year: 2020-2099 (reasonable range)
- Month: 01-12
- Day: 01-31 (valid for month)
- Date must be ≤ today (no future dates)

---

## 3. Optional CHANGELOG Fields

### 3.1 Version Metadata

**Deployment Status:**
```markdown
## [17.1.0] - 2025-12-10

**Status:** Production ✅  
**Deployed:** 2025-12-10 14:30:00 UTC  
**ELO Estimate:** 1650-1700 (50 games vs v17.0)
```

**Behavior if Missing:**
- Status defaults to "unknown"
- Deployment timestamp defaults to release date
- ELO estimate NULL (no performance data)

### 3.2 Version Links

**Format:**
```markdown
[17.1.0]: https://github.com/pssnyder/v7p3r-chess-engine/releases/tag/v17.1.0
```

**Behavior if Missing:**
- Links not required for ingestion
- Used for documentation purposes only

---

## 4. Data Type Specifications

### 4.1 Version Number Parsing

**Input:** `[17.1.0]` (brackets in header)  
**Output:** `17.1.0` (STRING)  
**Regex:** `\[(\d+\.\d+\.\d+)\]`

**Normalization:**
- Remove brackets: `[17.1.0]` → `17.1.0`
- Preserve leading zeros if present: `[01.02.03]` → `01.02.03`

### 4.2 Release Date Parsing

**Input:** `2025-12-10`  
**Output:** DATE `2025-12-10`

**Conversion to BigQuery:**
- ISO date string directly converts to DATE type
- No timezone handling needed (release date is date-only)

### 4.3 Description Extraction

**Input:**
```markdown
### Added
- Bishop pair bonus (+30cp when both bishops present)
- Isolated pawn penalty (-15cp per isolated pawn)
```

**Output:** Concatenated description
```
Added: Bishop pair bonus (+30cp when both bishops present), Isolated pawn penalty (-15cp per isolated pawn)
```

**Aggregation Logic:**
- Combine all change categories into single description field
- Preserve category headers (`Added:`, `Changed:`, etc.)
- Comma-separate items within category

---

## 5. Version Mapping Algorithm

### 5.1 Game Date → Version Lookup

**Procedure:**
1. Extract game date from PGN `[Date "YYYY.MM.DD"]` header
2. Convert to ISO date: `YYYY-MM-DD`
3. Query `engine_versions` table for version where:
   - `release_date ≤ game_date`
   - `next_version_release_date > game_date` (or NULL if latest version)
4. Assign `engine_version` to game record

**Example:**
- Game date: `2025-12-12`
- CHANGELOG versions:
  - v17.0.0: released 2025-12-05
  - v17.1.0: released 2025-12-10
  - v17.2.0: released 2025-12-15
- Lookup result: **v17.1.0** (game falls in 2025-12-10 to 2025-12-14 range)

### 5.2 Ambiguity Handling

**Multiple Games on Release Date:**
- If game date == release date: Assign new version
- Assumption: Versions deployed at start of day (00:00:00 UTC)

**Unknown Version (No Matching Date):**
- If game date < earliest CHANGELOG version: Assign NULL
- If game date > latest CHANGELOG version: Assign latest version (with warning)

---

## 6. Validation Rules

### 6.1 CHANGELOG File Validation

**Check Sequence:**
1. Verify file exists: `CHANGELOG.md` in repo root
2. Verify Markdown format (parseable)
3. Verify at least 1 version entry present
4. For each version entry:
   - Validate version header format `## [X.Y.Z] - YYYY-MM-DD`
   - Validate date is valid ISO date
   - Validate version number is semantic versioning
   - Verify at least 1 change category present

**Failure Action:**
- Log error to `operational_events`
- Ingestion continues (use existing version mappings)
- Alert user to fix CHANGELOG

### 6.2 Version Consistency Checks

**Chronological Order:**
- Version dates must be strictly increasing
- Example: v17.0.0 (2025-12-05) must be before v17.1.0 (2025-12-10)

**Version Number Order:**
- Version numbers should increase (major, minor, or patch)
- Example: v17.0.0 → v17.1.0 → v17.1.1 (valid)
- Example: v17.1.0 → v17.0.0 (invalid, decreasing)

**Duplicate Detection:**
- No duplicate version numbers
- No duplicate release dates (two versions on same day allowed but discouraged)

---

## 7. Expansion Rules

### 7.1 Allowed Expansions

**New Change Categories:**
- Example: `### Security` for security fixes
- Example: `### Testing` for test coverage improvements
- Categories ignored if not in standard set

**New Metadata Fields:**
- Example: `**Branch:** feature/time-manager`
- Example: `**Rollback:** v17.0.0 (regression detected)`
- Metadata parsed as key-value pairs

### 7.2 Breaking Changes

**Forbidden:**
- Changing version header format (must remain `## [X.Y.Z] - YYYY-MM-DD`)
- Changing date format (must remain ISO 8601)
- Removing historical version entries (immutable history)

**Allowed with Migration:**
- Changing version numbering scheme (e.g., switch to CalVer)
- Requires contract update and ingestion script modification

---

## 8. Integration with Conformed Layer

### 8.1 Target Schema

```sql
CREATE TABLE conformed_layer.engine_versions (
  version_number STRING NOT NULL PRIMARY KEY,  -- e.g., "17.1.0"
  release_date DATE NOT NULL,                  -- e.g., "2025-12-10"
  description STRING,                          -- Concatenated changes
  deployment_status STRING,                    -- "production", "testing", "rollback"
  elo_estimate INTEGER,                        -- Estimated ELO (if benchmarked)
  ingested_at TIMESTAMP
);
```

### 8.2 ETL Logic

**Ingestion Steps:**
1. Parse CHANGELOG.md
2. Extract all version entries (regex `## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})`)
3. For each version:
   - Extract version number, release date
   - Extract all change descriptions
   - Combine descriptions into single text field
4. Insert to `engine_versions` table (upsert logic for updates)
5. Validate chronological order and version consistency

---

## 9. Examples

### 9.1 Valid CHANGELOG Entry

```markdown
## [17.1.0] - 2025-12-10

**Status:** Production ✅  
**ELO Estimate:** 1680 (52% win rate vs v17.0, 100 games)

### Added
- Bishop pair bonus (+30cp when both bishops present)
- Isolated pawn penalty (-15cp per isolated pawn)

### Changed
- Lowered repetition threshold from 200cp to 50cp

### Fixed
- Fix PV instant move bug causing time forfeit

### Performance
- 10% faster move generation in middlegame positions

### Testing
- Added mate-in-3 regression test (v17.4 failure case)
- Regression suite now 100% passing
```

**Result:** ✅ PASS - All required fields present, valid format

### 9.2 Minimal Valid Entry

```markdown
## [17.0.0] - 2025-12-05

### Added
- Time manager integration
```

**Result:** ✅ PASS - Minimal but valid

### 9.3 Invalid Entry (Bad Date Format)

```markdown
## [17.1.0] - 12/10/2025

### Added
- Bishop pair bonus
```

**Result:** ❌ FAIL - Date format should be `2025-12-10` not `12/10/2025`

### 9.4 Invalid Entry (Missing Version Number)

```markdown
## Latest Version - 2025-12-10

### Added
- Bishop pair bonus
```

**Result:** ❌ FAIL - Version number must be semantic versioning `[X.Y.Z]`

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-30 | Initial contract created | V7P3R Analytics Team |

---

## 11. References

**Keep a Changelog:**
- https://keepachangelog.com/

**Semantic Versioning:**
- https://semver.org/

**Related Contracts:**
- `pgn_game_source_contract.md` - PGN game files (uses version mapping)
- `json_analysis_source_contract.md` - Stockfish analysis JSON

**Governed Resources:**
- Source File: `v7p3r-chess-engine/CHANGELOG.md`
- Ingestion Script: `scripts/ingestion/02_ingest_engine_versions.py`
- Target Table: `conformed_layer.engine_versions`

---

**Contract Owner:** V7P3R Analytics Team  
**Last Updated:** 2026-04-30  
**Next Review:** Quarterly (July 2026)
