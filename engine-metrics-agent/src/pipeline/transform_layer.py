#!/usr/bin/env python3
"""
Transform Layer Implementation
Creates chess-specific analytics views and features in BigQuery
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ChessTransformLayer:
    """Implements chess-specific transform layer in BigQuery"""
    
    def __init__(self):
        """Initialize transform layer"""
        try:
            from google.cloud import bigquery
            self.bigquery = bigquery
            self.client = bigquery.Client(project='chess-engine-metrics-agent')
            self.project_id = 'chess-engine-metrics-agent'
            self.raw_dataset = 'chess_engine_data_lake'
            self.transform_dataset = 'chess_analytics'
            
            # Ensure transform dataset exists
            self._create_transform_dataset()
            
        except ImportError:
            raise RuntimeError("BigQuery client not available")
    
    def _create_transform_dataset(self):
        """Create transform dataset if it doesn't exist"""
        try:
            dataset_ref = self.client.dataset(self.transform_dataset)
            self.client.get_dataset(dataset_ref)
            print(f"✅ Transform dataset exists: {self.transform_dataset}")
        except Exception:
            dataset = self.bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            dataset = self.client.create_dataset(dataset)
            print(f"✅ Created transform dataset: {self.transform_dataset}")
    
    def create_engine_performance_view(self) -> bool:
        """Create comprehensive engine performance view"""
        view_sql = f"""
        CREATE OR REPLACE VIEW `{self.project_id}.{self.transform_dataset}.engine_performance` AS
        WITH game_stats AS (
            -- Calculate per-engine statistics
            SELECT 
                engine,
                COUNT(*) as total_games,
                SUM(wins) as total_wins,
                SUM(losses) as total_losses,
                SUM(draws) as total_draws,
                ROUND(SUM(wins) * 100.0 / COUNT(*), 2) as win_rate,
                ROUND(SUM(draws) * 100.0 / COUNT(*), 2) as draw_rate,
                AVG(opponent_rating) as avg_opponent_rating,
                MIN(game_date) as first_game,
                MAX(game_date) as last_game,
                COUNTIF(DATE_DIFF(CURRENT_DATE(), game_date, DAY) <= 30) as games_last_30_days
            FROM (
                -- White games
                SELECT 
                    white as engine,
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as wins,
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as losses,
                    CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END as draws,
                    black_elo as opponent_rating,
                    date as game_date
                FROM `{self.project_id}.{self.raw_dataset}.pgn_games`
                WHERE white IS NOT NULL
                
                UNION ALL
                
                -- Black games  
                SELECT 
                    black as engine,
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as wins,
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as losses,
                    CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END as draws,
                    white_elo as opponent_rating,
                    date as game_date
                FROM `{self.project_id}.{self.raw_dataset}.pgn_games`
                WHERE black IS NOT NULL
            )
            GROUP BY engine
        ),
        engine_versions AS (
            -- Extract engine versions and families
            SELECT 
                engine,
                CASE 
                    WHEN REGEXP_CONTAINS(engine, r'V7P3R|v7p3r') THEN 'V7P3R'
                    WHEN REGEXP_CONTAINS(engine, r'C0BR4|c0br4') THEN 'C0BR4'  
                    WHEN REGEXP_CONTAINS(engine, r'SlowMate|slowmate') THEN 'SlowMate'
                    ELSE 'Other'
                END as engine_family,
                REGEXP_EXTRACT(engine, r'[vV]?(\d+\.?\d*\.?\d*)') as version_number
            FROM game_stats
        ),
        performance_ratings AS (
            -- Calculate estimated performance ratings
            SELECT 
                gs.engine,
                gs.total_games,
                gs.total_wins,
                gs.total_losses, 
                gs.total_draws,
                gs.win_rate,
                gs.draw_rate,
                gs.avg_opponent_rating,
                gs.first_game,
                gs.last_game,
                gs.games_last_30_days,
                ev.engine_family,
                ev.version_number,
                -- Estimate Elo performance (simplified)
                CASE 
                    WHEN gs.avg_opponent_rating IS NOT NULL THEN
                        ROUND(gs.avg_opponent_rating + 400 * LOG10(gs.win_rate / (100 - gs.win_rate)), 0)
                    ELSE NULL
                END as estimated_elo,
                -- Activity score (games played recently with recency weight)
                ROUND(gs.games_last_30_days * 2.0 + gs.total_games * 0.1, 1) as activity_score,
                -- Overall strength score (combination of win rate and opponent strength)
                ROUND(
                    gs.win_rate * 
                    COALESCE(gs.avg_opponent_rating / 1200.0, 1.0) * 
                    LOG10(GREATEST(gs.total_games, 10)) / 2.0, 
                    1
                ) as strength_score
            FROM game_stats gs
            LEFT JOIN engine_versions ev ON gs.engine = ev.engine
        )
        SELECT 
            *,
            CURRENT_TIMESTAMP() as last_updated,
            -- Rank engines by performance
            ROW_NUMBER() OVER (ORDER BY strength_score DESC) as overall_rank,
            ROW_NUMBER() OVER (PARTITION BY engine_family ORDER BY strength_score DESC) as family_rank
        FROM performance_ratings
        WHERE total_games >= 5  -- Only include engines with meaningful sample size
        ORDER BY strength_score DESC
        """
        
        try:
            self.client.query(view_sql).result()
            print("✅ Created engine_performance view")
            return True
        except Exception as e:
            print(f"❌ Failed to create engine_performance view: {e}")
            return False
    
    def create_head_to_head_view(self) -> bool:
        """Create head-to-head matchup analysis view"""
        view_sql = f"""
        CREATE OR REPLACE VIEW `{self.project_id}.{self.transform_dataset}.head_to_head` AS
        WITH direct_matchups AS (
            SELECT 
                white as engine_1,
                black as engine_2,
                result,
                date as game_date,
                move_count,
                opening
            FROM `{self.project_id}.{self.raw_dataset}.pgn_games`
            WHERE white IS NOT NULL AND black IS NOT NULL
        ),
        h2h_stats AS (
            SELECT 
                engine_1,
                engine_2,
                COUNT(*) as total_games,
                SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) as engine_1_wins,
                SUM(CASE WHEN result = '0-1' THEN 1 ELSE 0 END) as engine_2_wins,
                SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END) as draws,
                ROUND(SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as engine_1_win_rate,
                AVG(move_count) as avg_game_length,
                MIN(game_date) as first_encounter,
                MAX(game_date) as last_encounter,
                ARRAY_AGG(DISTINCT opening IGNORE NULLS LIMIT 5) as common_openings
            FROM direct_matchups
            GROUP BY engine_1, engine_2
        ),
        bidirectional_h2h AS (
            -- Create bidirectional matchups (A vs B and B vs A combined)
            SELECT 
                CASE WHEN engine_1 < engine_2 THEN engine_1 ELSE engine_2 END as engine_a,
                CASE WHEN engine_1 < engine_2 THEN engine_2 ELSE engine_1 END as engine_b,
                SUM(total_games) as total_games,
                SUM(CASE WHEN engine_1 < engine_2 THEN engine_1_wins ELSE engine_2_wins END) as engine_a_wins,
                SUM(CASE WHEN engine_1 < engine_2 THEN engine_2_wins ELSE engine_1_wins END) as engine_b_wins,
                SUM(draws) as total_draws,
                MIN(first_encounter) as first_encounter,
                MAX(last_encounter) as last_encounter
            FROM h2h_stats
            GROUP BY 
                CASE WHEN engine_1 < engine_2 THEN engine_1 ELSE engine_2 END,
                CASE WHEN engine_1 < engine_2 THEN engine_2 ELSE engine_1 END
        )
        SELECT 
            engine_a,
            engine_b,
            total_games,
            engine_a_wins,
            engine_b_wins,
            total_draws,
            ROUND(engine_a_wins * 100.0 / total_games, 1) as engine_a_win_rate,
            ROUND(engine_b_wins * 100.0 / total_games, 1) as engine_b_win_rate,
            ROUND(total_draws * 100.0 / total_games, 1) as draw_rate,
            first_encounter,
            last_encounter,
            DATE_DIFF(last_encounter, first_encounter, DAY) as rivalry_duration_days,
            -- Statistical significance (basic)
            CASE 
                WHEN total_games >= 20 THEN 'High'
                WHEN total_games >= 10 THEN 'Medium'
                ELSE 'Low'
            END as statistical_confidence,
            CURRENT_TIMESTAMP() as last_updated
        FROM bidirectional_h2h
        WHERE total_games >= 3  -- Only meaningful rivalries
        ORDER BY total_games DESC, ABS(engine_a_wins - engine_b_wins) DESC
        """
        
        try:
            self.client.query(view_sql).result()
            print("✅ Created head_to_head view")
            return True
        except Exception as e:
            print(f"❌ Failed to create head_to_head view: {e}")
            return False
    
    def create_development_timeline_view(self) -> bool:
        """Create engine development tracking view"""
        view_sql = f"""
        CREATE OR REPLACE VIEW `{self.project_id}.{self.transform_dataset}.development_timeline` AS
        WITH version_performance AS (
            SELECT 
                engine,
                MIN(date) as version_first_seen,
                MAX(date) as version_last_seen,
                COUNT(*) as games_played,
                ROUND(SUM(CASE 
                    WHEN (white = engine AND result = '1-0') OR (black = engine AND result = '0-1') 
                    THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate
            FROM `{self.project_id}.{self.raw_dataset}.pgn_games`
            WHERE (white IS NOT NULL OR black IS NOT NULL)
            GROUP BY engine
        ),
        engine_families AS (
            SELECT 
                *,
                CASE 
                    WHEN REGEXP_CONTAINS(engine, r'V7P3R|v7p3r') THEN 'V7P3R'
                    WHEN REGEXP_CONTAINS(engine, r'C0BR4|c0br4') THEN 'C0BR4'  
                    WHEN REGEXP_CONTAINS(engine, r'SlowMate|slowmate') THEN 'SlowMate'
                    ELSE 'Other'
                END as family,
                REGEXP_EXTRACT(engine, r'[vV]?(\d+\.?\d*\.?\d*)') as version_number,
                REGEXP_EXTRACT(engine, r'(\d+)') as major_version
            FROM version_performance
        ),
        version_trends AS (
            SELECT 
                *,
                -- Calculate improvement over previous versions in same family
                LAG(win_rate) OVER (
                    PARTITION BY family 
                    ORDER BY version_first_seen
                ) as previous_version_win_rate,
                LAG(version_first_seen) OVER (
                    PARTITION BY family 
                    ORDER BY version_first_seen  
                ) as previous_version_date
            FROM engine_families
            WHERE family != 'Other'
        )
        SELECT 
            engine,
            family,
            version_number,
            major_version,
            version_first_seen as release_date,
            version_last_seen as last_activity,
            games_played,
            win_rate,
            previous_version_win_rate,
            CASE 
                WHEN previous_version_win_rate IS NOT NULL 
                THEN ROUND(win_rate - previous_version_win_rate, 2)
                ELSE NULL
            END as win_rate_improvement,
            CASE 
                WHEN previous_version_date IS NOT NULL
                THEN DATE_DIFF(version_first_seen, previous_version_date, DAY)
                ELSE NULL  
            END as days_since_previous_version,
            -- Development velocity (improvements per day)
            CASE 
                WHEN previous_version_date IS NOT NULL AND previous_version_win_rate IS NOT NULL
                THEN ROUND(
                    (win_rate - previous_version_win_rate) / 
                    GREATEST(DATE_DIFF(version_first_seen, previous_version_date, DAY), 1), 
                    4
                )
                ELSE NULL
            END as improvement_velocity,
            CURRENT_TIMESTAMP() as last_updated
        FROM version_trends
        WHERE games_played >= 5
        ORDER BY family, version_first_seen
        """
        
        try:
            self.client.query(view_sql).result()
            print("✅ Created development_timeline view") 
            return True
        except Exception as e:
            print(f"❌ Failed to create development_timeline view: {e}")
            return False
    
    def create_ai_agent_summary_table(self) -> bool:
        """Create optimized summary table for AI agent queries"""
        table_sql = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.transform_dataset}.ai_agent_insights` AS
        WITH latest_engine_stats AS (
            SELECT * FROM `{self.project_id}.{self.transform_dataset}.engine_performance`
            WHERE total_games >= 10
        ),
        recent_development AS (
            SELECT * FROM `{self.project_id}.{self.transform_dataset}.development_timeline`  
            WHERE release_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        ),
        key_rivalries AS (
            SELECT * FROM `{self.project_id}.{self.transform_dataset}.head_to_head`
            WHERE total_games >= 10 AND statistical_confidence IN ('High', 'Medium')
        )
        SELECT 
            'engine_summary' as insight_type,
            les.engine as subject,
            les.engine_family as category,
            STRUCT(
                les.total_games,
                les.win_rate,
                les.estimated_elo,
                les.overall_rank,
                les.activity_score,
                les.strength_score,
                les.games_last_30_days
            ) as performance_metrics,
            STRUCT(
                rd.win_rate_improvement,
                rd.improvement_velocity,
                rd.days_since_previous_version
            ) as development_metrics,
            ARRAY(
                SELECT STRUCT(engine_b, total_games, engine_a_win_rate, engine_b_win_rate)
                FROM key_rivalries kr 
                WHERE kr.engine_a = les.engine OR kr.engine_b = les.engine
                ORDER BY total_games DESC
                LIMIT 5
            ) as key_rivalries,
            CURRENT_TIMESTAMP() as last_updated
        FROM latest_engine_stats les
        LEFT JOIN recent_development rd ON les.engine = rd.engine
        WHERE les.total_games >= 10
        
        UNION ALL
        
        SELECT 
            'family_summary' as insight_type,
            engine_family as subject,
            'engine_family' as category,
            STRUCT(
                SUM(total_games) as total_games,
                ROUND(AVG(win_rate), 2) as avg_win_rate,
                ROUND(AVG(estimated_elo), 0) as avg_elo,
                COUNT(*) as family_size,
                ROUND(AVG(activity_score), 1) as avg_activity,
                ROUND(MAX(strength_score), 1) as best_strength_score,
                SUM(games_last_30_days) as recent_games
            ) as performance_metrics,
            NULL as development_metrics,
            NULL as key_rivalries,
            CURRENT_TIMESTAMP() as last_updated
        FROM latest_engine_stats
        GROUP BY engine_family
        """
        
        try:
            self.client.query(table_sql).result()
            print("✅ Created ai_agent_insights table")
            return True
        except Exception as e:
            print(f"❌ Failed to create ai_agent_insights table: {e}")
            return False
    
    def deploy_transform_layer(self) -> bool:
        """Deploy complete transform layer"""
        print("🚀 Deploying Chess Engine Transform Layer")
        print("=" * 50)
        
        success_count = 0
        total_count = 4
        
        transforms = [
            ("Engine Performance View", self.create_engine_performance_view),
            ("Head-to-Head Analysis View", self.create_head_to_head_view), 
            ("Development Timeline View", self.create_development_timeline_view),
            ("AI Agent Summary Table", self.create_ai_agent_summary_table)
        ]
        
        for name, func in transforms:
            print(f"\n📊 Creating {name}...")
            if func():
                success_count += 1
            else:
                print(f"❌ Failed: {name}")
        
        print(f"\n{'='*50}")
        print(f"📊 Transform Layer Deployment: {success_count}/{total_count} successful")
        
        if success_count == total_count:
            print("🎉 Transform Layer deployment COMPLETE!")
            return True
        else:
            print("⚠️  Partial deployment - some views failed")
            return False

def main():
    """Main deployment function"""
    try:
        transform = ChessTransformLayer()
        success = transform.deploy_transform_layer()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Transform layer deployment failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())