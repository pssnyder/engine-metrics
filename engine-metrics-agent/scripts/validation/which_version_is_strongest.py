#!/usr/bin/env python3
"""
Which V7P3R Version Is Strongest?

Analyzes engine versions using opponent-adjusted metrics:
1. Quality-adjusted win rate (weighted by opponent strength)
2. Performance vs expected score (ELO theory)
3. Composite strength score (0-100)
"""
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "chess-engine-metrics-agent"
client = bigquery.Client(project=PROJECT_ID)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

print("=" * 120)
print("WHICH V7P3R VERSION IS STRONGEST? (Opponent-Adjusted Analysis)")
print("=" * 120)

query = """
WITH version_performance AS (
  SELECT
    engine_version,
    COUNT(*) as total_games,
    
    -- Basic metrics
    COUNTIF(outcome = 'win') as wins,
    COUNTIF(outcome = 'draw') as draws,
    COUNTIF(outcome = 'loss') as losses,
    ROUND(COUNTIF(outcome = 'win') * 100.0 / COUNT(*), 1) as raw_win_pct,
    
    -- ELO metrics
    ROUND(AVG(v7p3r_elo), 0) as avg_v7p3r_elo,
    ROUND(AVG(opponent_elo), 0) as avg_opponent_elo,
    ROUND(AVG(opponent_elo - v7p3r_elo), 0) as avg_elo_diff,
    
    -- Opponent strength distribution
    COUNTIF(relative_opponent_strength = 'stronger') as vs_stronger_count,
    COUNTIF(relative_opponent_strength = 'equal') as vs_equal_count,
    COUNTIF(relative_opponent_strength = 'weaker') as vs_weaker_count,
    
    -- Quality-adjusted win rate (weighted by opponent strength)
    -- Stronger opponent wins count more, weaker opponent wins count less
    ROUND(
      SUM(
        CASE
          WHEN outcome = 'win' AND relative_opponent_strength = 'stronger' THEN 1.5
          WHEN outcome = 'win' AND relative_opponent_strength = 'equal' THEN 1.0
          WHEN outcome = 'win' AND relative_opponent_strength = 'weaker' THEN 0.75
          WHEN outcome = 'draw' AND relative_opponent_strength = 'stronger' THEN 0.75
          WHEN outcome = 'draw' AND relative_opponent_strength = 'equal' THEN 0.5
          WHEN outcome = 'draw' AND relative_opponent_strength = 'weaker' THEN 0.375
          ELSE 0
        END
      ) * 100.0 / COUNT(*),
      1
    ) as quality_adjusted_win_pct,
    
    -- Expected score vs actual score (ELO theory)
    ROUND(AVG(expected_score) * 100, 1) as expected_score_pct,
    ROUND(AVG(actual_score) * 100, 1) as actual_score_pct,
    ROUND((AVG(actual_score) - AVG(expected_score)) * 100, 1) as performance_vs_expected,
    
    -- Strength of schedule (higher opponent ELO = tougher schedule)
    CASE
      WHEN AVG(opponent_elo) >= 1600 THEN 'very_hard'
      WHEN AVG(opponent_elo) >= 1500 THEN 'hard'
      WHEN AVG(opponent_elo) >= 1400 THEN 'moderate'
      ELSE 'easy'
    END as schedule_difficulty
    
  FROM `chess-engine-metrics-agent.conformed_layer.game_data_enhanced`
  WHERE engine_version IS NOT NULL
    AND is_v7p3r_elo_reliable = TRUE
  GROUP BY engine_version
),
composite_scoring AS (
  SELECT
    *,
    
    -- Composite Strength Score (0-100)
    -- 40% quality-adjusted win rate
    -- 30% performance vs expected
    -- 20% avg ELO
    -- 10% schedule difficulty bonus
    ROUND(
      (quality_adjusted_win_pct * 0.4) +
      ((performance_vs_expected + 20) * 1.5) +  -- Normalize performance_vs_expected to 0-40 scale
      ((avg_v7p3r_elo - 1200) / 10) +  -- Normalize ELO to 0-20 scale
      (CASE schedule_difficulty
        WHEN 'very_hard' THEN 10
        WHEN 'hard' THEN 7
        WHEN 'moderate' THEN 4
        ELSE 0
      END),
      1
    ) as composite_strength_score,
    
    -- Confidence level (based on sample size)
    CASE
      WHEN total_games >= 500 THEN 'very_high'
      WHEN total_games >= 200 THEN 'high'
      WHEN total_games >= 100 THEN 'medium'
      WHEN total_games >= 50 THEN 'low'
      ELSE 'very_low'
    END as confidence
    
  FROM version_performance
)
SELECT *
FROM composite_scoring
WHERE total_games >= 50  -- Only versions with meaningful sample size
ORDER BY composite_strength_score DESC
"""

print("\n[Calculating opponent-adjusted performance metrics...]")
print("-" * 120)

result = client.query(query).to_dataframe()

# Display results
print("\nV7P3R VERSION STRENGTH RANKING")
print("=" * 120)
print("\nKEY METRICS EXPLANATION:")
print("  • Quality-Adjusted Win %: Weights wins by opponent strength (stronger=1.5x, equal=1.0x, weaker=0.75x)")
print("  • Performance vs Expected: How much better/worse than ELO theory predicts")
print("  • Composite Strength Score: Combines all factors (0-100, higher = stronger)")
print("-" * 120)

# Rank 1-5
top_5 = result.head(5)
print(f"\n{'Rank':<6}{'Version':<12}{'Games':<8}{'Quality Win%':<14}{'Perf vs Exp':<13}{'Composite':<11}{'Confidence':<12}{'Avg ELO':<10}")
print("-" * 120)
for idx, row in top_5.iterrows():
    rank = idx + 1
    print(f"{rank:<6}{row['engine_version']:<12}{row['total_games']:<8}{row['quality_adjusted_win_pct']:<14.1f}{row['performance_vs_expected']:<13.1f}{row['composite_strength_score']:<11.1f}{row['confidence']:<12}{int(row['avg_v7p3r_elo']):<10}")

print("\n" + "=" * 120)
print("\n📊 DETAILED BREAKDOWN - TOP 3 VERSIONS")
print("=" * 120)

for idx in range(min(3, len(result))):
    row = result.iloc[idx]
    print(f"\n#{idx+1} {row['engine_version']} - Composite Score: {row['composite_strength_score']:.1f}/100 ({row['confidence']} confidence)")
    print("-" * 120)
    print(f"  Games Played:           {row['total_games']} ({row['wins']}W / {row['draws']}D / {row['losses']}L)")
    print(f"  Raw Win Rate:           {row['raw_win_pct']:.1f}%")
    print(f"  Quality-Adjusted Win:   {row['quality_adjusted_win_pct']:.1f}%")
    print(f"  Expected Score:         {row['expected_score_pct']:.1f}%")
    print(f"  Actual Score:           {row['actual_score_pct']:.1f}%")
    print(f"  Performance vs Expected: {row['performance_vs_expected']:+.1f}%")
    print(f"  Avg V7P3R ELO:          {int(row['avg_v7p3r_elo'])}")
    print(f"  Avg Opponent ELO:       {int(row['avg_opponent_elo'])} (Δ{int(row['avg_elo_diff']):+d})")
    print(f"  Opponent Strength:      {row['vs_stronger_count']} stronger / {row['vs_equal_count']} equal / {row['vs_weaker_count']} weaker")
    print(f"  Schedule Difficulty:    {row['schedule_difficulty']}")

print("\n" + "=" * 120)
print("✓ ANALYSIS COMPLETE")
print("=" * 120)

# Export to CSV for further analysis
output_file = "../../reporting_datasets/v7p3r_version_strength_ranking.csv"
result.to_csv(output_file, index=False)
print(f"\n✓ Full results saved to: {output_file}")
print("=" * 120)
