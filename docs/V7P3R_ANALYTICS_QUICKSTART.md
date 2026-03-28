# V7P3R Analytics Pipeline - Quick Start

**Status:** ✅ Complete | Lichess-Style Insights Operational

---

## What We Built

A **local analytics pipeline** for V7P3R chess engine gameplay with multi-dimensional insights.

### Results
- ✅ **18,336 games** extracted from PGN files
- ✅ **1.35 million moves** parsed
- ✅ **Multi-dimensional slicing** (like Lichess Insights)
- ✅ **Automated reporting** with version tracking

---

## Quick Start (3 Commands)

### 1. Extract Data
```powershell
cd "e:\Programming Stuff\Chess Engines\Chess Engine Playground\engine-metrics\reporting_scripts"

# Extract game metadata (18k games)
python extract_game_data.py

# Extract move-level data (1.35M moves)
python extract_move_data.py
```

### 2. Generate Reports
```powershell
# Basic metrics (last 30 days)
python generate_gameplay_report.py

# Comprehensive insights
python generate_insights_report.py
```

### 3. View Results
```powershell
# Check reports folder
cd "..\reports"
dir

# View latest insights
type "insights\comprehensive_insights_latest.txt"
```

---

## Available Insights

### Dimensions You Can Slice By
- **Opponent Strength** - ELO brackets (<1400, 1400-1600, 1600-1800, etc.)
- **Color** - White vs Black
- **Time Control** - Bullet, Blitz, Rapid, Classical
- **Opening Family** - Sicilian, Queen's Gambit, Italian Game, etc.
- **Castling Patterns** - Kingside, Queenside, None
- **Queen Trades** - With/without queen trades
- **Engine Version** - v12.x, v14.x, v17.x
- **Month** - Temporal trends

### Metrics You Can Analyze
- Win Rate %
- Loss Rate %
- Draw Rate %
- Average Game Length
- ELO Change per Game
- Games Played

---

## Sample Insights (From Latest Report)

### Win Rate by Opponent Strength
| Opponent ELO | Win Rate | Games |
|--------------|----------|-------|
| <1400        | 59.80%   | 6,983 |
| 1400-1600    | 34.37%   | 5,618 |
| 1600-1800    | 18.25%   | 2,992 |
| 2200+        | 3.20%    | 531   |

### Best Engine Version
| Version | Win Rate | Games |
|---------|----------|-------|
| v17.1   | 70.54%   | 224   |
| v17.2.0 | 48.90%   | 636   |
| v17.4   | 47.02%   | 504   |
| v17.5   | 41.61%   | 6,378 |

### Castling Impact
| Pattern   | Win Rate | Games  |
|-----------|----------|--------|
| Queenside | 46.75%   | 1,063  |
| None      | 37.85%   | 13,019 |
| Kingside  | 34.49%   | 4,254  |

---

## Data Files

### Datasets (`reporting_datasets/`)
- `v7p3r_game_data_latest.csv` - 18,336 games
- `v7p3r_moves_latest.csv` - 1,350,163 moves
- `v7p3r_game_summary_enhanced_latest.csv` - Enhanced summaries

### Reports (`reports/`)
- `v7p3r_recent_gameplay_report_latest.txt` - Last 30 days
- `v7p3r_version_comparison_report_latest.txt` - Version metrics
- `insights/comprehensive_insights_latest.txt` - Multi-dimensional insights

---

## Custom Analysis

Want to slice differently? Edit `generate_insights_report.py`:

```python
from generate_insights_report import DataLoader, InsightsEngine

loader = DataLoader()
engine = InsightsEngine(loader)

# Example: Win rate by opponent strength + color
results = engine.multi_dimensional_analysis(
    primary_dim='opponent_strength',
    secondary_dim='color',
    metric='win_rate'
)
```

---

## Adding New Data

1. Download PGN from Lichess → `raw_data/game_records/Lichess V7P3R Bot/`
2. Update `CHANGELOG.md` if new version
3. Re-run ETL:
   ```powershell
   python extract_game_data.py
   python extract_move_data.py
   python generate_insights_report.py
   ```

**Refresh Time:** ~5 minutes

---

## Architecture

```
PGN Files → ETL Scripts → CSV Datasets → Analytics Engine → Reports
```

**Full Documentation:** See `ENHANCED_INSIGHTS_FRAMEWORK_DESIGN.md`

---

## Key Findings

✅ **Strengths:**
- 59.80% win rate vs <1400 ELO
- Queenside castling performs best (46.75%)
- v17.1 best version (70.54%)

⚠️ **Weaknesses:**
- 3.20% vs 2200+ ELO
- v17.5 regression (41.61%)
- Kingside castling underperforms (34.49%)

📈 **Trends:**
- December 2025 peak (53.49%)
- March 2026 recovery (43.86%)

---

**Ready to Analyze!** 🚀

See `docs/ENHANCED_INSIGHTS_FRAMEWORK_DESIGN.md` for full details.
