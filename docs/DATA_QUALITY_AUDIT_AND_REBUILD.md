# V7P3R ENGINE METRICS - DATA QUALITY AUDIT & REBUILD PLAN
**Date**: 2026-05-04  
**Status**: CRITICAL - Current reporting layer invalid due to fundamental data quality issues

---

## 🚨 ISSUES DISCOVERED (From Colab Notebook Analysis)

### 1. **Duplicates Inflating Metrics**
- Historical data dumps contained overlapping game records
- Rolling uploads of "to-date" records from v7p3r_bot created duplicates
- Same game counted multiple times → inflated win counts, total games

### 2. **Game Type Confusion**
- No distinction between rated, casual, and testing games
- **Rated games**: ELO is reliable, competitive environment
- **Casual games**: ELO is unreliable, experimental play
- **Testing games**: Internal development, non-representative
- Current metrics treat all games equally → misleading rankings

### 3. **Misrepresented Engine Performance**
- **Raw win ratio problem**: Engine A with 90% win rate vs weak opponents (1200 ELO) ranks higher than Engine B with 60% win rate vs strong opponents (1800 ELO)
- **Reality**: Engine B is objectively stronger but appears weaker
- **Legacy engines**: Old versions played against weak opponents early on, inflating their win rates

### 4. **Missing Opponent-Relative Metrics**
- No `relative_opponent_strength` (stronger/weaker/equal)
- No `weighted_win_score` (wins vs stronger opponents worth more)
- No `expected_score` based on ELO theory
- No `performance_vs_expected` (overperformance indicator)

### 5. **Lack of Contextual Performance**
- No per-opponent performance tracking (Engine A vs Engine B head-to-head)
- No per-time-control analysis (bullet/blitz/rapid/classical)
- No per-opening-family performance

---

## 📋 REBUILD PLAN

### Phase 1: Conformed Layer Data Quality Audit ✅ SCRIPTS READY
**Scripts Created**:
- `scripts/validation/01_check_duplicates.sql` - Detect duplicate game_ids
- `scripts/validation/run_validation.py` - Execute all validation queries

**Actions**:
1. Run duplicate detection across all tables
2. Identify source of duplicates (raw_layer vs conformed_layer)
3. Create deduplication strategy
4. Document duplicate game_ids for removal

---

### Phase 2: Enhance Conformed Layer Schema 🔄 IN PROGRESS

#### 2.1 Add Game Type Classification
**New Column**: `game_type` (STRING)
- **Derivation**: Parse `event` column
  - `event LIKE '%rated%'` → `'rated'`
  - `event LIKE '%casual%'` → `'casual'`
  - Other → `'testing'` (requires validation)

#### 2.2 Add ELO Reliability Flags
**New Columns**: 
- `is_v7p3r_elo_reliable` (BOOLEAN)
- `is_opponent_elo_reliable` (BOOLEAN)
- **Logic**: `game_type = 'rated'` → `TRUE`, else `FALSE`

#### 2.3 Add Opponent Strength Classification
**New Column**: `relative_opponent_strength` (STRING)
- **Values**: `'stronger'`, `'weaker'`, `'equal'`, `'unknown'`
- **Logic** (only if both ELOs reliable):
  ```sql
  CASE
    WHEN opponent_elo > v7p3r_elo THEN 'stronger'
    WHEN opponent_elo < v7p3r_elo THEN 'weaker'
    WHEN opponent_elo = v7p3r_elo THEN 'equal'
    ELSE 'unknown'
  END
  ```

#### 2.4 Add Expected Performance Metrics
**New Columns**:
- `expected_score` (FLOAT): ELO theory prediction
  - Formula: `1 / (1 + 10^((opponent_elo - v7p3r_elo) / 400))`
- `actual_score` (FLOAT): Actual game result
  - Win = 1.0, Draw = 0.5, Loss = 0.0

---

### Phase 3: Rebuild Reporting Layer with Opponent-Adjusted Metrics ✅ SCRIPTS READY

**Scripts Created**:
- `scripts/validation/02_opponent_adjusted_performance.sql` - Quality-adjusted win rates
- `scripts/validation/03_strongest_version_analysis.sql` - Composite strength scoring

#### 3.1 Version Performance Metrics (REPLACE CURRENT)
**New Metrics**:
1. `raw_win_rate` - Simple wins/total (for reference only)
2. `quality_adjusted_win_rate` - Weighted by opponent strength ⭐
3. `expected_score` - ELO-predicted performance
4. `performance_vs_expected` - Overperformance indicator ⭐
5. `strength_of_schedule` - Average opponent difficulty
6. `composite_strength_score` - Weighted combination (0-100 scale) ⭐⭐⭐

**Weighting for Composite Score**:
- Quality-adjusted win rate: 40%
- Performance vs expected: 30%
- Average ELO: 20%
- Strength of schedule: 10%

#### 3.2 Per-Opponent Performance
**New Table**: `reporting_layer.head_to_head_performance`
- `v7p3r_version` (STRING)
- `opponent_username` (STRING)
- `games_played` (INT)
- `wins`, `losses`, `draws` (INT)
- `win_rate`, `quality_adjusted_win_rate` (FLOAT)

#### 3.3 Per-Time-Control Performance (ENHANCE CURRENT)
**Add Metrics**:
- `quality_adjusted_win_rate` (weighted by opponent ELO)
- `performance_vs_expected`
- `avg_opponent_elo` (strength of schedule)

---

### Phase 4: Validation & Answer Key Question ✅ SCRIPTS READY

**Question**: "Which v7p3r version is strongest?"

**Answer Method** (from `03_strongest_version_analysis.sql`):
1. Calculate composite strength score for each version (min 50 games)
2. Rank by composite score (accounts for opponent quality)
3. Verify with multiple metrics (quality-adjusted win rate, overperformance, peak ELO)
4. Assign confidence level based on sample size and consistency

**Expected Outputs**:
- Overall rank (1 = strongest)
- Composite strength score (0-100)
- Quality-adjusted win rate
- Performance vs expected
- Sample size and confidence level

---

## 🎯 IMMEDIATE NEXT STEPS

### Step 1: Run Duplicate Detection (NOW)
```bash
cd scripts/validation
python run_validation.py
```
**Expected**: Identify how many duplicate game_ids exist

### Step 2: Create Conformed Layer Enhancement Script
- Deduplicate game_data
- Add game_type, ELO reliability, opponent strength
- Add expected_score and actual_score
- Create backup before making changes

### Step 3: Rebuild Reporting Layer
- Delete current reporting tables (they're invalid)
- Recreate with opponent-adjusted metrics
- Use validation scripts to verify rankings

### Step 4: Answer "Which Version Is Strongest?"
- Run `03_strongest_version_analysis.sql`
- Compare to user's understanding
- Validate that rankings make sense (newer versions should generally rank higher if development is progressing)

---

## 📊 METRICS COMPARISON

### OLD (INVALID) METRICS
- ❌ Raw win ratio (ignores opponent strength)
- ❌ Simple game count (includes duplicates)
- ❌ All games treated equally (rated + casual + testing)
- ❌ Legacy engines appear strongest (weak opponent bias)

### NEW (VALID) METRICS
- ✅ Quality-adjusted win rate (weighted by opponent ELO)
- ✅ Performance vs expected (ELO-theory based)
- ✅ Composite strength score (multi-factor ranking)
- ✅ Rated games only (reliable ELO)
- ✅ Deduplicated game records
- ✅ Opponent-relative performance

---

## 🔧 TECHNICAL IMPLEMENTATION

### Conformed Layer Update Query (DRAFT)
```sql
-- Create enhanced game_data table
CREATE OR REPLACE TABLE `chess-engine-metrics-agent.conformed_layer.game_data_v2` AS
WITH deduplicated AS (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ingested_at DESC) as row_num
    FROM `chess-engine-metrics-agent.conformed_layer.game_data`
  )
  WHERE row_num = 1
),
enhanced AS (
  SELECT
    *,
    -- Game type classification
    CASE
      WHEN LOWER(event) LIKE '%rated%' THEN 'rated'
      WHEN LOWER(event) LIKE '%casual%' THEN 'casual'
      ELSE 'testing'
    END as game_type,
    
    -- ELO reliability
    LOWER(event) LIKE '%rated%' as is_v7p3r_elo_reliable,
    LOWER(event) LIKE '%rated%' as is_opponent_elo_reliable,
    
    -- Opponent strength (only if ELOs reliable)
    CASE
      WHEN LOWER(event) LIKE '%rated%' THEN
        CASE
          WHEN opponent_elo > v7p3r_elo THEN 'stronger'
          WHEN opponent_elo < v7p3r_elo THEN 'weaker'
          WHEN opponent_elo = v7p3r_elo THEN 'equal'
          ELSE 'unknown'
        END
      ELSE 'unknown'
    END as relative_opponent_strength,
    
    -- Expected score (ELO theory)
    CASE
      WHEN LOWER(event) LIKE '%rated%' THEN
        1.0 / (1.0 + POW(10, (opponent_elo - v7p3r_elo) / 400.0))
      ELSE NULL
    END as expected_score,
    
    -- Actual score
    CASE
      WHEN outcome = 'win' THEN 1.0
      WHEN outcome = 'draw' THEN 0.5
      ELSE 0.0
    END as actual_score
    
  FROM deduplicated
)
SELECT * FROM enhanced;
```

---

## 📝 NOTES FROM COLAB NOTEBOOK ANALYSIS

### Key Insights (From User's Exploration)
1. **ELO Reliability Critical**: Only rated games provide trustworthy ELO data
2. **Weighted Win Scores**: Wins vs stronger opponents should count more
   - Stronger opponent win: 1.5 points
   - Equal opponent win: 1.0 points
   - Weaker opponent win: 0.75 points
3. **Game Type Categorization**: Proposed schema enhancement for BigQuery
4. **Pairwise Performance**: Need head-to-head records between versions
5. **Simple Win Ratios Misleading**: Example from notebook shows this clearly

### Proposed BigQuery Schema Enhancements (From Notebook)
- [x] `game_type` column (implemented above)
- [x] ELO reliability flags (implemented above)
- [x] `relative_opponent_strength` (implemented above)
- [ ] Aggregated tables for pairwise performance (TODO)
- [ ] Materialized views for common queries (TODO)

---

## ✅ SUCCESS CRITERIA

### Data Quality
- [ ] Zero duplicate game_ids in conformed layer
- [ ] All games have valid `game_type` classification
- [ ] ELO reliability flags correctly set
- [ ] Opponent strength categorized for all rated games

### Reporting Metrics
- [ ] Quality-adjusted win rates calculated for all versions
- [ ] Composite strength scores assign reasonable rankings
- [ ] Strongest version identified matches user understanding
- [ ] Confidence levels assigned based on sample size

### Validation
- [ ] Duplicate detection returns 0 inflated records
- [ ] Opponent-adjusted performance shows different rankings than raw win rate
- [ ] Strongest version analysis produces consistent, defensible results
- [ ] All reporting tables refreshed with valid data

---

**Status**: Ready to execute Phase 1 (duplicate detection) and proceed with rebuild
