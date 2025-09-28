#!/usr/bin/env python3
"""
Dashboard & AI Integration Test
Shows the reporting layer data ready for visualization and AI queries
"""

from google.cloud import bigquery

def test_dashboard_ready_data():
    client = bigquery.Client(project='chess-engine-metrics-agent')
    
    print("🎨 DASHBOARD & AI INTEGRATION READINESS TEST")
    print("=" * 60)
    
    # 1. KPI Dashboard Summary  
    print("\n1️⃣ EXECUTIVE DASHBOARD KPIs")
    print("-" * 35)
    
    kpi_query = """
    SELECT 
        v7p3r_main_engine_count,
        v7p3r_avg_win_rate,
        v7p3r_best_win_rate,
        v7p3r_best_rank,
        v7p3r_engines_top10,
        v7p3r_market_share,
        v7p3r_vs_ecosystem_advantage
    FROM `chess-engine-metrics-agent.chess_reporting.dashboard_kpis`
    """
    
    kpis = list(client.query(kpi_query).result())[0]
    
    print("🎯 V7P3R ENGINE PORTFOLIO:")
    print(f"  • {kpis['v7p3r_main_engine_count']} main engine versions tracked")
    print(f"  • {kpis['v7p3r_avg_win_rate']}% average win rate across all versions")
    print(f"  • {kpis['v7p3r_best_win_rate']}% peak performance (best version)")
    print(f"  • #{kpis['v7p3r_best_rank']} best global ranking achieved")
    print(f"  • {kpis['v7p3r_engines_top10']} versions in global top 10")
    print(f"  • {kpis['v7p3r_market_share']}% market share (games played)")
    print(f"  • {kpis['v7p3r_vs_ecosystem_advantage']:+.1f}% advantage over ecosystem average")
    
    # 2. Performance Summary Cards
    print(f"\n2️⃣ ENGINE PERFORMANCE SUMMARY CARDS")
    print("-" * 45)
    
    summary_query = """
    SELECT 
        engine,
        performance_category,
        win_rate,
        overall_rank,
        activity_level,
        v7p3r_version
    FROM `chess-engine-metrics-agent.chess_reporting.engine_summary_stats`
    WHERE is_v7p3r_main = TRUE
    ORDER BY win_rate DESC
    LIMIT 5
    """
    
    print("🏆 TOP 5 V7P3R MAIN ENGINES:")
    for engine in client.query(summary_query).result():
        print(f"  • {engine['engine']:<20} | v{engine['v7p3r_version']} | {engine['performance_category']:<12} | {engine['win_rate']:>5.1f}% | Rank #{engine['overall_rank']:<3} | {engine['activity_level']}")
    
    # 3. Development Timeline Data
    print(f"\n3️⃣ DEVELOPMENT TIMELINE (READY FOR CHARTS)")  
    print("-" * 50)
    
    timeline_query = """
    SELECT 
        version_number,
        development_phase,
        win_rate,
        performance_trend,
        win_rate_improvement,
        v7p3r_performance_rank
    FROM `chess-engine-metrics-agent.chess_reporting.v7p3r_development_timeline`
    ORDER BY major_version_num, minor_version_num
    LIMIT 8
    """
    
    print("📈 V7P3R DEVELOPMENT PROGRESSION:")
    for version in client.query(timeline_query).result():
        trend_icon = {"Strong Improvement": "🚀", "Improving": "📈", "Stable": "➡️", "Minor Decline": "📉", "Significant Decline": "⬇️"}.get(version['performance_trend'], "❓")
        improvement = f"{version['win_rate_improvement']:+.1f}%" if version['win_rate_improvement'] else "N/A"
        print(f"  • v{version['version_number']:<6} | {version['development_phase']:<18} | {version['win_rate']:>5.1f}% | Δ: {improvement:>6} | Rank #{version['v7p3r_performance_rank']} {trend_icon}")
    
    # 4. Head-to-Head Matrix Sample
    print(f"\n4️⃣ HEAD-TO-HEAD RIVALRY MATRIX")
    print("-" * 40)
    
    rivalry_query = """
    SELECT 
        engine_b as opponent,
        total_games,
        engine_a_win_rate as v7p3r_win_rate,
        rivalry_type,
        confidence_level
    FROM `chess-engine-metrics-agent.chess_reporting.head_to_head_matrix`
    WHERE engine_a_family = 'V7P3R_Main'
    ORDER BY total_games DESC
    LIMIT 5
    """
    
    print("⚔️  TOP V7P3R RIVALRIES:")
    for rivalry in client.query(rivalry_query).result():
        print(f"  • vs {rivalry['opponent']:<25} | {rivalry['total_games']:>3} games | {rivalry['v7p3r_win_rate']:>5.1f}% win rate | {rivalry['rivalry_type']:<15} | {rivalry['confidence_level']}")
    
    # 5. AI Agent Query Examples
    print(f"\n5️⃣ AI AGENT READY INSIGHTS")
    print("-" * 35)
    
    print("🤖 SAMPLE AI QUERIES YOUR SYSTEM CAN NOW ANSWER:")
    print("   • 'How has V7P3R improved over time?'")
    print("   • 'What's V7P3R's competitive position?'")  
    print("   • 'Which V7P3R version performs best against SlowMate?'")
    print("   • 'Show me V7P3R's development velocity trends'")
    print("   • 'What's V7P3R's market share in the chess engine ecosystem?'")
    
    # 6. Data Freshness
    reporting_tables = [
        'engine_summary_stats',
        'daily_performance_trends', 
        'head_to_head_matrix',
        'v7p3r_development_timeline',
        'dashboard_kpis'
    ]
    
    print(f"\n6️⃣ DATA PIPELINE STATUS")
    print("-" * 30)
    
    for table in reporting_tables:
        count_query = f"SELECT COUNT(*) as count FROM `chess-engine-metrics-agent.chess_reporting.{table}`"
        count = list(client.query(count_query).result())[0]['count']
        print(f"  ✅ {table:<30}: {count:>6,} records")
    
    print(f"\n🎉 PIPELINE FULLY OPERATIONAL!")
    print(f"   🔄 Raw → Transform → Reporting layers complete")
    print(f"   🎨 Ready for dashboard visualization integration") 
    print(f"   🤖 Ready for AI chat enhancement")
    print(f"   ☁️  All data in Google Cloud BigQuery")

if __name__ == "__main__":
    test_dashboard_ready_data()