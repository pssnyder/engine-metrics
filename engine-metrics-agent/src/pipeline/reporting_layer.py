#!/usr/bin/env python3
"""
Chess Engine Reporting Layer
Creates dashboard-optimized data aggregations for visualization
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ChessReportingLayer:
    """Creates dashboard-optimized reporting tables"""
    
    def __init__(self):
        """Initialize reporting layer"""
        try:
            from google.cloud import bigquery
            self.bigquery = bigquery
            self.client = bigquery.Client(project='chess-engine-metrics-agent')
            self.project_id = 'chess-engine-metrics-agent'
            self.transform_dataset = 'chess_analytics'
            self.reporting_dataset = 'chess_reporting'
            
            # Ensure reporting dataset exists
            self._create_reporting_dataset()
            
        except ImportError:
            raise RuntimeError("BigQuery client not available")
    
    def _create_reporting_dataset(self):
        """Create reporting dataset if it doesn't exist"""
        try:
            dataset_ref = self.client.dataset(self.reporting_dataset)
            self.client.get_dataset(dataset_ref)
            print(f"✅ Reporting dataset exists: {self.reporting_dataset}")
        except Exception:
            dataset = self.bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            dataset = self.client.create_dataset(dataset)
            print(f"✅ Created reporting dataset: {self.reporting_dataset}")
    
    def create_engine_summary_stats(self) -> bool:
        """Create engine summary statistics for dashboard cards"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.reporting_dataset}.engine_summary_stats` AS
        SELECT 
            engine,
            engine_family,
            
            -- Core Performance Metrics
            total_games,
            win_rate,
            draw_rate,
            estimated_elo,
            
            -- Rankings
            overall_rank,
            family_rank,
            
            -- Strength Indicators  
            strength_score,
            activity_score,
            
            -- Recent Activity
            games_last_30_days,
            CASE 
                WHEN games_last_30_days > 50 THEN 'Very Active'
                WHEN games_last_30_days > 20 THEN 'Active'
                WHEN games_last_30_days > 5 THEN 'Moderate'
                ELSE 'Low Activity'
            END as activity_level,
            
            -- Performance Categories
            CASE 
                WHEN win_rate >= 60 THEN 'Excellent'
                WHEN win_rate >= 45 THEN 'Good'  
                WHEN win_rate >= 30 THEN 'Average'
                ELSE 'Needs Improvement'
            END as performance_category,
            
            -- V7P3R Specific Flags
            CASE 
                WHEN engine_family = 'V7P3R_Main' THEN TRUE
                ELSE FALSE
            END as is_v7p3r_main,
            
            CASE 
                WHEN engine_family = 'V7P3R_Experimental_AI' THEN TRUE
                ELSE FALSE
            END as is_v7p3r_ai,
            
            -- Version extraction for V7P3R engines
            CASE 
                WHEN engine_family LIKE 'V7P3R%' THEN 
                    REGEXP_EXTRACT(engine, r'[vV]([0-9]+\.?[0-9]*\.?[0-9]*)')
                ELSE NULL
            END as v7p3r_version,
            
            last_updated
            
        FROM `{self.project_id}.{self.transform_dataset}.engine_performance`
        WHERE total_games >= 5  -- Only meaningful sample sizes
        ORDER BY strength_score DESC
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created engine_summary_stats table")
            return True
        except Exception as e:
            print(f"❌ Failed to create engine_summary_stats: {e}")
            return False
    
    def create_daily_performance_trends(self) -> bool:
        """Create time-series performance data for trend charts"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.reporting_dataset}.daily_performance_trends` AS
        WITH daily_games AS (
            -- Aggregate games by day and engine
            SELECT 
                date as game_date,
                white as engine,
                CASE WHEN result = '1-0' THEN 1 ELSE 0 END as wins,
                1 as games_played
            FROM `{self.project_id}.chess_engine_data_lake.pgn_games`
            WHERE white IS NOT NULL
            
            UNION ALL
            
            SELECT 
                date as game_date,
                black as engine,
                CASE WHEN result = '0-1' THEN 1 ELSE 0 END as wins,
                1 as games_played
            FROM `{self.project_id}.chess_engine_data_lake.pgn_games`
            WHERE black IS NOT NULL
        ),
        daily_stats AS (
            SELECT 
                game_date,
                engine,
                SUM(games_played) as daily_games,
                SUM(wins) as daily_wins,
                ROUND(SUM(wins) * 100.0 / SUM(games_played), 1) as daily_win_rate
            FROM daily_games
            GROUP BY game_date, engine
        ),
        rolling_averages AS (
            SELECT 
                *,
                -- 7-day rolling average
                ROUND(AVG(daily_win_rate) OVER (
                    PARTITION BY engine 
                    ORDER BY game_date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ), 1) as win_rate_7day_avg,
                
                -- 30-day rolling average
                ROUND(AVG(daily_win_rate) OVER (
                    PARTITION BY engine 
                    ORDER BY game_date 
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                ), 1) as win_rate_30day_avg,
                
                -- Cumulative stats
                SUM(daily_games) OVER (
                    PARTITION BY engine 
                    ORDER BY game_date
                ) as cumulative_games,
                
                SUM(daily_wins) OVER (
                    PARTITION BY engine 
                    ORDER BY game_date
                ) as cumulative_wins
                
            FROM daily_stats
        )
        SELECT 
            *,
            ROUND(cumulative_wins * 100.0 / cumulative_games, 1) as cumulative_win_rate,
            
            -- Engine family classification
            CASE 
                WHEN REGEXP_CONTAINS(engine, r'V7P3R') AND NOT REGEXP_CONTAINS(engine, r'AI') THEN 'V7P3R_Main'
                WHEN REGEXP_CONTAINS(engine, r'V7P3RAI') THEN 'V7P3R_Experimental_AI'
                WHEN REGEXP_CONTAINS(engine, r'SlowMate') THEN 'SlowMate'
                WHEN REGEXP_CONTAINS(engine, r'Stockfish') THEN 'Stockfish'
                ELSE 'Other'
            END as engine_family,
            
            CURRENT_TIMESTAMP() as last_updated
            
        FROM rolling_averages
        WHERE daily_games >= 3  -- Only days with meaningful activity
        ORDER BY engine, game_date
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created daily_performance_trends table")
            return True
        except Exception as e:
            print(f"❌ Failed to create daily_performance_trends: {e}")
            return False
    
    def create_head_to_head_matrix(self) -> bool:
        """Create comprehensive rivalry matrix for heatmap visualizations"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.reporting_dataset}.head_to_head_matrix` AS
        SELECT 
            engine_a,
            engine_b,
            total_games,
            engine_a_wins,
            engine_b_wins,
            total_draws,
            engine_a_win_rate,
            engine_b_win_rate,
            draw_rate,
            
            -- Rivalry intensity metrics
            ABS(engine_a_win_rate - engine_b_win_rate) as competitiveness_gap,
            CASE 
                WHEN ABS(engine_a_win_rate - engine_b_win_rate) <= 10 THEN 'Very Competitive'
                WHEN ABS(engine_a_win_rate - engine_b_win_rate) <= 25 THEN 'Competitive'
                WHEN ABS(engine_a_win_rate - engine_b_win_rate) <= 50 THEN 'One-Sided'
                ELSE 'Dominant'
            END as rivalry_type,
            
            -- Statistical significance
            statistical_confidence,
            CASE 
                WHEN statistical_confidence = 'High' AND total_games >= 50 THEN 'Statistically Significant'
                WHEN statistical_confidence = 'High' THEN 'High Confidence'
                WHEN statistical_confidence = 'Medium' THEN 'Medium Confidence'
                ELSE 'Low Confidence'
            END as confidence_level,
            
            -- Engine family classifications for filtering
            CASE 
                WHEN REGEXP_CONTAINS(engine_a, r'V7P3R') AND NOT REGEXP_CONTAINS(engine_a, r'AI') THEN 'V7P3R_Main'
                WHEN REGEXP_CONTAINS(engine_a, r'V7P3RAI') THEN 'V7P3R_Experimental_AI'
                WHEN REGEXP_CONTAINS(engine_a, r'SlowMate') THEN 'SlowMate'
                WHEN REGEXP_CONTAINS(engine_a, r'Stockfish') THEN 'Stockfish'
                ELSE 'Other'
            END as engine_a_family,
            
            CASE 
                WHEN REGEXP_CONTAINS(engine_b, r'V7P3R') AND NOT REGEXP_CONTAINS(engine_b, r'AI') THEN 'V7P3R_Main'
                WHEN REGEXP_CONTAINS(engine_b, r'V7P3RAI') THEN 'V7P3R_Experimental_AI'
                WHEN REGEXP_CONTAINS(engine_b, r'SlowMate') THEN 'SlowMate'
                WHEN REGEXP_CONTAINS(engine_b, r'Stockfish') THEN 'Stockfish'
                ELSE 'Other'
            END as engine_b_family,
            
            -- V7P3R specific flags
            CASE 
                WHEN (REGEXP_CONTAINS(engine_a, r'V7P3R') OR REGEXP_CONTAINS(engine_b, r'V7P3R')) THEN TRUE
                ELSE FALSE
            END as involves_v7p3r,
            
            rivalry_duration_days,
            first_encounter,
            last_encounter,
            last_updated
            
        FROM `{self.project_id}.{self.transform_dataset}.head_to_head`
        ORDER BY total_games DESC, competitiveness_gap ASC
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created head_to_head_matrix table")
            return True
        except Exception as e:
            print(f"❌ Failed to create head_to_head_matrix: {e}")
            return False
    
    def create_v7p3r_development_timeline(self) -> bool:
        """Create V7P3R-specific development progression analysis"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.reporting_dataset}.v7p3r_development_timeline` AS
        WITH v7p3r_versions AS (
            SELECT 
                engine,
                family,
                version_number,
                release_date,
                last_activity,
                games_played,
                win_rate,
                win_rate_improvement,
                days_since_previous_version,
                improvement_velocity,
                
                -- Extract numeric version for proper sorting
                CAST(REGEXP_EXTRACT(version_number, r'^(\d+)') AS FLOAT64) as major_version_num,
                CAST(REGEXP_EXTRACT(version_number, r'\.(\d+)') AS FLOAT64) as minor_version_num,
                
                -- Development phase classification
                CASE 
                    WHEN CAST(REGEXP_EXTRACT(version_number, r'^(\d+)') AS FLOAT64) <= 4 THEN 'Early Development'
                    WHEN CAST(REGEXP_EXTRACT(version_number, r'^(\d+)') AS FLOAT64) <= 7 THEN 'Maturation Phase'
                    WHEN CAST(REGEXP_EXTRACT(version_number, r'^(\d+)') AS FLOAT64) <= 10 THEN 'Advanced Development'
                    ELSE 'Latest Versions'
                END as development_phase,
                
                last_updated
                
            FROM `{self.project_id}.{self.transform_dataset}.development_timeline`
            WHERE family = 'V7P3R_Main'  -- Only main V7P3R engines
        ),
        performance_trends AS (
            SELECT 
                *,
                -- Performance trend indicators
                LAG(win_rate, 1) OVER (ORDER BY major_version_num, minor_version_num) as previous_win_rate,
                LAG(win_rate, 2) OVER (ORDER BY major_version_num, minor_version_num) as two_versions_ago_win_rate,
                
                -- Momentum indicators
                CASE 
                    WHEN win_rate_improvement > 5 THEN 'Strong Improvement'
                    WHEN win_rate_improvement > 0 THEN 'Improving'
                    WHEN win_rate_improvement = 0 THEN 'Stable'
                    WHEN win_rate_improvement > -5 THEN 'Minor Decline'
                    ELSE 'Significant Decline'
                END as performance_trend,
                
                -- Release cadence analysis
                CASE 
                    WHEN days_since_previous_version <= 7 THEN 'Rapid Release'
                    WHEN days_since_previous_version <= 30 THEN 'Regular Release'
                    WHEN days_since_previous_version <= 90 THEN 'Moderate Release'
                    ELSE 'Slow Release'
                END as release_cadence
                
            FROM v7p3r_versions
        )
        SELECT 
            *,
            -- Best version indicators
            win_rate = MAX(win_rate) OVER () as is_best_version,
            games_played = MAX(games_played) OVER () as is_most_tested,
            
            -- Cumulative improvements
            SUM(COALESCE(win_rate_improvement, 0)) OVER (
                ORDER BY major_version_num, minor_version_num 
                ROWS UNBOUNDED PRECEDING
            ) as cumulative_improvement,
            
            -- Rank within V7P3R family
            ROW_NUMBER() OVER (ORDER BY win_rate DESC) as v7p3r_performance_rank,
            
            CURRENT_TIMESTAMP() as reporting_last_updated
            
        FROM performance_trends
        ORDER BY major_version_num, minor_version_num
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created v7p3r_development_timeline table")
            return True
        except Exception as e:
            print(f"❌ Failed to create v7p3r_development_timeline: {e}")
            return False
    
    def create_dashboard_kpis(self) -> bool:
        """Create key performance indicators for dashboard summary cards"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.reporting_dataset}.dashboard_kpis` AS
        WITH base_metrics AS (
            SELECT 
                -- V7P3R Main Engine KPIs
                COUNT(CASE WHEN engine_family = 'V7P3R_Main' THEN 1 END) as v7p3r_main_engine_count,
                ROUND(AVG(CASE WHEN engine_family = 'V7P3R_Main' THEN win_rate END), 1) as v7p3r_avg_win_rate,
                MAX(CASE WHEN engine_family = 'V7P3R_Main' THEN win_rate END) as v7p3r_best_win_rate,
                MIN(CASE WHEN engine_family = 'V7P3R_Main' AND overall_rank IS NOT NULL THEN overall_rank END) as v7p3r_best_rank,
                SUM(CASE WHEN engine_family = 'V7P3R_Main' THEN total_games END) as v7p3r_total_games,
                
                -- Overall Ecosystem KPIs
                COUNT(*) as total_engines_analyzed,
                ROUND(AVG(win_rate), 1) as ecosystem_avg_win_rate,
                MAX(win_rate) as ecosystem_best_win_rate,
                SUM(total_games) as ecosystem_total_games,
                
                -- Competitive Position
                COUNT(CASE WHEN engine_family = 'V7P3R_Main' AND overall_rank <= 10 THEN 1 END) as v7p3r_engines_top10,
                COUNT(CASE WHEN engine_family = 'V7P3R_Main' AND performance_category IN ('Excellent', 'Good') THEN 1 END) as v7p3r_strong_performers,
                
                -- Activity Metrics
                SUM(CASE WHEN engine_family = 'V7P3R_Main' THEN games_last_30_days END) as v7p3r_recent_activity,
                COUNT(CASE WHEN engine_family = 'V7P3R_Main' AND activity_level IN ('Active', 'Very Active') THEN 1 END) as v7p3r_active_engines
                
            FROM `{self.project_id}.{self.reporting_dataset}.engine_summary_stats`
        ),
        rivalry_metrics AS (
            SELECT 
                COUNT(CASE WHEN involves_v7p3r THEN 1 END) as v7p3r_rivalries,
                COUNT(CASE WHEN involves_v7p3r AND confidence_level = 'Statistically Significant' THEN 1 END) as v7p3r_significant_rivalries,
                AVG(CASE WHEN involves_v7p3r AND engine_a_family = 'V7P3R_Main' THEN engine_a_win_rate 
                         WHEN involves_v7p3r AND engine_b_family = 'V7P3R_Main' THEN engine_b_win_rate END) as v7p3r_rivalry_win_rate
            FROM `{self.project_id}.{self.reporting_dataset}.head_to_head_matrix`
        ),
        development_metrics AS (
            SELECT 
                COUNT(*) as v7p3r_versions_tracked,
                MAX(win_rate) as v7p3r_peak_performance,
                AVG(CASE WHEN win_rate_improvement > 0 THEN win_rate_improvement END) as v7p3r_avg_improvement,
                COUNT(CASE WHEN performance_trend IN ('Strong Improvement', 'Improving') THEN 1 END) as v7p3r_improving_versions
            FROM `{self.project_id}.{self.reporting_dataset}.v7p3r_development_timeline`
        )
        SELECT 
            -- V7P3R Performance Summary
            bm.v7p3r_main_engine_count,
            bm.v7p3r_avg_win_rate,
            bm.v7p3r_best_win_rate,
            bm.v7p3r_best_rank,
            bm.v7p3r_total_games,
            
            -- Competitive Position
            bm.v7p3r_engines_top10,
            bm.v7p3r_strong_performers,
            ROUND(bm.v7p3r_engines_top10 * 100.0 / bm.total_engines_analyzed, 1) as v7p3r_top10_percentage,
            
            -- Market Share & Activity
            ROUND(bm.v7p3r_total_games * 100.0 / bm.ecosystem_total_games, 1) as v7p3r_market_share,
            bm.v7p3r_recent_activity,
            bm.v7p3r_active_engines,
            
            -- Rivalry Performance
            rm.v7p3r_rivalries,
            rm.v7p3r_significant_rivalries,
            ROUND(rm.v7p3r_rivalry_win_rate, 1) as v7p3r_rivalry_win_rate,
            
            -- Development Progress
            dm.v7p3r_versions_tracked,
            dm.v7p3r_peak_performance,
            ROUND(dm.v7p3r_avg_improvement, 1) as v7p3r_avg_improvement,
            dm.v7p3r_improving_versions,
            
            -- Ecosystem Context
            bm.total_engines_analyzed,
            bm.ecosystem_avg_win_rate,
            bm.ecosystem_best_win_rate,
            bm.ecosystem_total_games,
            
            -- Performance vs Ecosystem
            ROUND(bm.v7p3r_avg_win_rate - bm.ecosystem_avg_win_rate, 1) as v7p3r_vs_ecosystem_advantage,
            
            CURRENT_TIMESTAMP() as last_updated
            
        FROM base_metrics bm
        CROSS JOIN rivalry_metrics rm  
        CROSS JOIN development_metrics dm
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created dashboard_kpis table")
            return True
        except Exception as e:
            print(f"❌ Failed to create dashboard_kpis: {e}")
            return False
    
    def deploy_reporting_layer(self) -> bool:
        """Deploy complete reporting layer for dashboards"""
        print("🚀 Deploying Chess Engine Reporting Layer")
        print("=" * 55)
        
        success_count = 0
        total_count = 5
        
        reports = [
            ("Engine Summary Stats", self.create_engine_summary_stats),
            ("Daily Performance Trends", self.create_daily_performance_trends),
            ("Head-to-Head Matrix", self.create_head_to_head_matrix),
            ("V7P3R Development Timeline", self.create_v7p3r_development_timeline),
            ("Dashboard KPIs", self.create_dashboard_kpis)
        ]
        
        for name, func in reports:
            print(f"\n📊 Creating {name}...")
            if func():
                success_count += 1
            else:
                print(f"❌ Failed: {name}")
        
        print(f"\n{'='*55}")
        print(f"📊 Reporting Layer Deployment: {success_count}/{total_count} successful")
        
        if success_count == total_count:
            print("🎉 Reporting Layer deployment COMPLETE!")
            print("🎨 Ready for dashboard visualization integration!")
            return True
        else:
            print("⚠️  Partial deployment - some reports failed")
            return False

def main():
    """Main deployment function"""
    try:
        reporting = ChessReportingLayer()
        success = reporting.deploy_reporting_layer()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Reporting layer deployment failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())