#!/usr/bin/env python3
"""
Comprehensive Transform Layer Verification
Validates all views, data integrity, and performance metrics
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add the pipeline directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def comprehensive_verification():
    """Complete verification of transform layer"""
    
    try:
        from google.cloud import bigquery
        
        project_id = 'chess-engine-metrics-agent'
        client = bigquery.Client(project=project_id)
        
        print("🔍 COMPREHENSIVE TRANSFORM LAYER VERIFICATION")
        print("=" * 60)
        
        verification_results = {
            'engine_performance': False,
            'head_to_head': False, 
            'development_timeline': False,
            'ai_agent_insights': False,
            'data_integrity': False
        }
        
        # 1. ENGINE PERFORMANCE VIEW VERIFICATION
        print(f"\n1️⃣ ENGINE PERFORMANCE VIEW VERIFICATION")
        print("-" * 45)
        
        try:
            perf_query = f"""
            SELECT 
                engine_family,
                COUNT(*) as engine_count,
                AVG(win_rate) as avg_win_rate,
                AVG(total_games) as avg_games,
                MAX(strength_score) as best_score
            FROM `{project_id}.chess_analytics.engine_performance`
            GROUP BY engine_family
            ORDER BY engine_count DESC
            """
            
            results = list(client.query(perf_query).result())
            
            if results:
                print(f"✅ Engine Performance View: {len(results)} engine families")
                
                v7p3r_main = None
                v7p3r_ai = None
                
                for family in results:
                    print(f"  {family['engine_family']:<25} | {family['engine_count']:>3} engines | Avg Win Rate: {family['avg_win_rate']:>5.1f}% | Best Score: {family['best_score']:>6.1f}")
                    
                    if family['engine_family'] == 'V7P3R_Main':
                        v7p3r_main = family
                    elif family['engine_family'] == 'V7P3R_Experimental_AI':
                        v7p3r_ai = family
                
                # Validate V7P3R separation
                if v7p3r_main and v7p3r_ai:
                    print(f"\n🎯 V7P3R CATEGORIZATION VERIFIED:")
                    print(f"  Main V7P3R Engines: {v7p3r_main['engine_count']} engines, {v7p3r_main['avg_win_rate']:.1f}% avg win rate")
                    print(f"  AI Experimental: {v7p3r_ai['engine_count']} engines, {v7p3r_ai['avg_win_rate']:.1f}% avg win rate")
                    verification_results['engine_performance'] = True
                else:
                    print(f"⚠️  V7P3R categorization incomplete")
                    
            else:
                print("❌ No engine performance data found")
                
        except Exception as e:
            print(f"❌ Engine Performance verification failed: {str(e)[:100]}...")
        
        # 2. HEAD-TO-HEAD VIEW VERIFICATION
        print(f"\n2️⃣ HEAD-TO-HEAD VIEW VERIFICATION")
        print("-" * 40)
        
        try:
            h2h_query = f"""
            SELECT 
                COUNT(*) as total_rivalries,
                AVG(total_games) as avg_games_per_rivalry,
                COUNT(CASE WHEN statistical_confidence = 'High' THEN 1 END) as high_confidence_rivalries,
                MAX(total_games) as biggest_rivalry_games
            FROM `{project_id}.chess_analytics.head_to_head`
            """
            
            h2h_stats = list(client.query(h2h_query).result())[0]
            print(f"✅ Head-to-Head Analysis:")
            print(f"  Total Rivalries: {h2h_stats['total_rivalries']}")
            print(f"  Avg Games per Rivalry: {h2h_stats['avg_games_per_rivalry']:.1f}")
            print(f"  High Confidence Rivalries: {h2h_stats['high_confidence_rivalries']}")
            print(f"  Biggest Rivalry: {h2h_stats['biggest_rivalry_games']} games")
            
            # Check V7P3R rivalries
            v7p3r_rivals_query = f"""
            SELECT 
                CASE WHEN engine_a LIKE '%V7P3R%' THEN engine_a ELSE engine_b END as v7p3r_engine,
                CASE WHEN engine_a LIKE '%V7P3R%' THEN engine_b ELSE engine_a END as opponent,
                total_games,
                CASE WHEN engine_a LIKE '%V7P3R%' THEN engine_a_win_rate ELSE engine_b_win_rate END as v7p3r_win_rate
            FROM `{project_id}.chess_analytics.head_to_head`
            WHERE engine_a LIKE '%V7P3R%' OR engine_b LIKE '%V7P3R%'
            ORDER BY total_games DESC
            LIMIT 5
            """
            
            v7p3r_rivals = list(client.query(v7p3r_rivals_query).result())
            if v7p3r_rivals:
                print(f"\n🎯 TOP V7P3R RIVALRIES:")
                for rival in v7p3r_rivals:
                    engine_type = "Main" if "AI" not in rival['v7p3r_engine'] else "AI"
                    print(f"  {rival['v7p3r_engine'][:20]} vs {rival['opponent'][:20]} | {rival['total_games']} games | {rival['v7p3r_win_rate']:.1f}% | {engine_type}")
                
                verification_results['head_to_head'] = True
            
        except Exception as e:
            print(f"❌ Head-to-Head verification failed: {str(e)[:100]}...")
        
        # 3. DEVELOPMENT TIMELINE VERIFICATION
        print(f"\n3️⃣ DEVELOPMENT TIMELINE VERIFICATION")
        print("-" * 42)
        
        try:
            timeline_query = f"""
            SELECT 
                family,
                COUNT(*) as version_count,
                MIN(release_date) as first_release,
                MAX(release_date) as latest_release,
                AVG(win_rate) as avg_family_win_rate
            FROM `{project_id}.chess_analytics.development_timeline`
            GROUP BY family
            ORDER BY version_count DESC
            """
            
            timeline_results = list(client.query(timeline_query).result())
            if timeline_results:
                print(f"✅ Development Timeline: {len(timeline_results)} engine families tracked")
                
                for family in timeline_results:
                    print(f"  {family['family']:<25} | {family['version_count']:>3} versions | {family['first_release']} → {family['latest_release']} | Avg: {family['avg_family_win_rate']:>5.1f}%")
                
                # Check V7P3R development progression
                v7p3r_dev_query = f"""
                SELECT 
                    engine,
                    version_number,
                    release_date,
                    win_rate,
                    win_rate_improvement
                FROM `{project_id}.chess_analytics.development_timeline`
                WHERE family = 'V7P3R_Main'
                ORDER BY release_date
                LIMIT 10
                """
                
                v7p3r_dev = list(client.query(v7p3r_dev_query).result())
                if v7p3r_dev:
                    print(f"\n🎯 V7P3R DEVELOPMENT PROGRESSION (First 10 versions):")
                    for version in v7p3r_dev:
                        improvement = f"{version['win_rate_improvement']:+.1f}%" if version['win_rate_improvement'] else "N/A"
                        print(f"  {version['engine']:<20} | {version['release_date']} | Win Rate: {version['win_rate']:>5.1f}% | Δ: {improvement:>6}")
                    
                    verification_results['development_timeline'] = True
                
        except Exception as e:
            print(f"❌ Development Timeline verification failed: {str(e)[:100]}...")
        
        # 4. AI AGENT INSIGHTS VERIFICATION
        print(f"\n4️⃣ AI AGENT INSIGHTS TABLE VERIFICATION")
        print("-" * 44)
        
        try:
            ai_insights_query = f"""
            SELECT 
                insight_type,
                COUNT(*) as record_count,
                COUNT(CASE WHEN category LIKE '%V7P3R%' THEN 1 END) as v7p3r_records
            FROM `{project_id}.chess_analytics.ai_agent_insights`
            GROUP BY insight_type
            ORDER BY record_count DESC
            """
            
            ai_results = list(client.query(ai_insights_query).result())
            if ai_results:
                print(f"✅ AI Agent Insights Table:")
                total_records = sum(r['record_count'] for r in ai_results)
                total_v7p3r = sum(r['v7p3r_records'] for r in ai_results)
                
                for insight in ai_results:
                    print(f"  {insight['insight_type']:<20} | {insight['record_count']:>4} records | V7P3R: {insight['v7p3r_records']:>2}")
                
                print(f"\n📊 SUMMARY: {total_records} total insights, {total_v7p3r} V7P3R-related")
                verification_results['ai_agent_insights'] = True
                
        except Exception as e:
            print(f"❌ AI Agent Insights verification failed: {str(e)[:100]}...")
        
        # 5. DATA INTEGRITY VERIFICATION
        print(f"\n5️⃣ DATA INTEGRITY VERIFICATION")
        print("-" * 35)
        
        try:
            # Cross-check raw data vs transformed data
            raw_count_query = f"""
            SELECT COUNT(*) as raw_games
            FROM `{project_id}.chess_engine_data_lake.pgn_games`
            """
            
            raw_count = list(client.query(raw_count_query).result())[0]['raw_games']
            
            # Count games in performance view (should be same engines but different aggregation)
            perf_games_query = f"""
            SELECT SUM(total_games) as transform_games
            FROM `{project_id}.chess_analytics.engine_performance`
            """
            
            transform_games = list(client.query(perf_games_query).result())[0]['transform_games']
            
            print(f"✅ Data Integrity Check:")
            print(f"  Raw Game Records: {raw_count:,}")
            print(f"  Transform Layer Games: {transform_games:,}")
            
            # Check for data consistency (each raw game should contribute to 2 engine records in transform)
            expected_transform_games = raw_count * 2  # Each game has 2 players
            accuracy = (transform_games / expected_transform_games) * 100 if expected_transform_games > 0 else 0
            
            print(f"  Expected Transform Games: {expected_transform_games:,}")
            print(f"  Data Accuracy: {accuracy:.1f}%")
            
            if accuracy >= 95:
                print(f"  ✅ Data integrity EXCELLENT")
                verification_results['data_integrity'] = True
            elif accuracy >= 90:
                print(f"  ⚠️  Data integrity GOOD (some edge cases)")
                verification_results['data_integrity'] = True
            else:
                print(f"  ❌ Data integrity issues detected")
            
        except Exception as e:
            print(f"❌ Data integrity verification failed: {str(e)[:100]}...")
        
        # FINAL SUMMARY
        print(f"\n📊 COMPREHENSIVE VERIFICATION SUMMARY")
        print("=" * 50)
        
        passed_checks = sum(verification_results.values())
        total_checks = len(verification_results)
        
        for check, status in verification_results.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {check.replace('_', ' ').title()}")
        
        print(f"\n🎯 OVERALL STATUS: {passed_checks}/{total_checks} checks passed")
        
        if passed_checks == total_checks:
            print("🎉 TRANSFORM LAYER FULLY VERIFIED AND OPERATIONAL!")
            return True
        elif passed_checks >= 4:
            print("⚠️  Transform layer mostly operational with minor issues")
            return True
        else:
            print("❌ Transform layer has significant issues requiring attention")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = comprehensive_verification()
    sys.exit(0 if success else 1)