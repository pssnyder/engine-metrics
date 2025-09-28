#!/usr/bin/env python3
"""
Quick AI Agent Insights Test
"""

from google.cloud import bigquery

def test_ai_insights():
    client = bigquery.Client(project='chess-engine-metrics-agent')
    
    print("🤖 TESTING AI AGENT INSIGHTS TABLE")
    print("=" * 40)
    
    # Test insight types
    query = """
    SELECT insight_type, COUNT(*) as count 
    FROM `chess-engine-metrics-agent.chess_analytics.ai_agent_insights` 
    GROUP BY insight_type
    """
    
    print("📊 INSIGHT TYPES:")
    for row in client.query(query).result():
        print(f"  {row.insight_type}: {row.count} records")
    
    # Test V7P3R insights
    v7p3r_query = """
    SELECT 
        subject, 
        category, 
        performance_metrics.win_rate, 
        performance_metrics.overall_rank
    FROM `chess-engine-metrics-agent.chess_analytics.ai_agent_insights`
    WHERE subject LIKE '%V7P3R%' AND subject NOT LIKE '%AI%'
    AND insight_type = 'engine_summary'
    ORDER BY performance_metrics.strength_score DESC
    LIMIT 3
    """
    
    print("\n🎯 TOP V7P3R MAIN ENGINES:")
    for row in client.query(v7p3r_query).result():
        print(f"  {row.subject}: Rank #{row.performance_metrics.overall_rank}, Win Rate: {row.performance_metrics.win_rate:.1f}%")
    
    print("\n✅ AI Agent Insights table is operational!")

if __name__ == "__main__":
    test_ai_insights()