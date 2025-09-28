#!/usr/bin/env python3
"""
Investigate V7P3R Engine Variants
Distinguish between V7P3R (main engine) and V7P3RAI (experimental AI)
"""

from google.cloud import bigquery

def investigate_v7p3r_engines():
    """Check all V7P3R engine variants in the data"""
    
    client = bigquery.Client(project='chess-engine-metrics-agent')
    
    print("🔍 INVESTIGATING V7P3R ENGINE VARIANTS")
    print("=" * 55)
    
    # Query for all V7P3R variants
    query = """
    WITH all_engines AS (
        SELECT white as engine FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`
        WHERE white LIKE '%V7P3R%'
        UNION DISTINCT
        SELECT black as engine FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`  
        WHERE black LIKE '%V7P3R%'
    )
    SELECT 
        engine,
        CASE 
            WHEN engine LIKE '%AI%' THEN 'Experimental AI'
            ELSE 'Main Engine'
        END as engine_type,
        (SELECT COUNT(*) FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games` 
         WHERE white = engine OR black = engine) as total_games
    FROM all_engines
    ORDER BY total_games DESC
    """
    
    results = list(client.query(query).result())
    
    if results:
        print(f"📊 FOUND {len(results)} V7P3R ENGINE VARIANTS:\n")
        
        main_engines = []
        ai_engines = []
        
        for row in results:
            engine_name = row.engine
            engine_type = row.engine_type  
            game_count = row.total_games
            
            print(f"  {engine_name:<35} | {game_count:>5} games | {engine_type}")
            
            if engine_type == 'Main Engine':
                main_engines.append((engine_name, game_count))
            else:
                ai_engines.append((engine_name, game_count))
        
        print(f"\n📈 SUMMARY:")
        print(f"  🎯 Main V7P3R Engines: {len(main_engines)}")
        print(f"  🤖 Experimental AI Engines: {len(ai_engines)}")
        
        if main_engines:
            total_main_games = sum(games for _, games in main_engines)
            print(f"  📊 Total Main Engine Games: {total_main_games:,}")
            
        if ai_engines:
            total_ai_games = sum(games for _, games in ai_engines)
            print(f"  🧪 Total AI Engine Games: {total_ai_games:,}")
            
        # Analyze performance comparison
        print(f"\n🏆 PERFORMANCE QUICK CHECK:")
        
        # Check main V7P3R performance
        if main_engines:
            main_perf_query = """
            WITH main_games AS (
                SELECT 
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as white_wins,
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as black_wins
                FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`
                WHERE white LIKE '%V7P3R%' AND white NOT LIKE '%AI%'
                
                UNION ALL
                
                SELECT 
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as white_wins,
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as black_wins  
                FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`
                WHERE black LIKE '%V7P3R%' AND black NOT LIKE '%AI%'
            )
            SELECT 
                COUNT(*) as total_games,
                SUM(white_wins) as total_wins,
                ROUND(SUM(white_wins) * 100.0 / COUNT(*), 1) as win_rate
            FROM main_games
            """
            
            main_results = list(client.query(main_perf_query).result())
            if main_results and main_results[0].total_games > 0:
                mr = main_results[0]
                print(f"  🎯 Main V7P3R Win Rate: {mr.win_rate}% ({mr.total_wins}/{mr.total_games} games)")
        
        # Check AI V7P3RAI performance  
        if ai_engines:
            ai_perf_query = """
            WITH ai_games AS (
                SELECT 
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as white_wins,
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as black_wins
                FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`
                WHERE white LIKE '%V7P3RAI%'
                
                UNION ALL
                
                SELECT 
                    CASE WHEN result = '0-1' THEN 1 ELSE 0 END as white_wins,
                    CASE WHEN result = '1-0' THEN 1 ELSE 0 END as black_wins  
                FROM `chess-engine-metrics-agent.chess_engine_data_lake.pgn_games`
                WHERE black LIKE '%V7P3RAI%'
            )
            SELECT 
                COUNT(*) as total_games,
                SUM(white_wins) as total_wins,
                ROUND(SUM(white_wins) * 100.0 / COUNT(*), 1) as win_rate
            FROM ai_games
            """
            
            ai_results = list(client.query(ai_perf_query).result())
            if ai_results and ai_results[0].total_games > 0:
                ar = ai_results[0]
                print(f"  🤖 Experimental AI Win Rate: {ar.win_rate}% ({ar.total_wins}/{ar.total_games} games)")
        
    else:
        print("❌ No V7P3R engines found in data!")
    
    print(f"\n💡 RECOMMENDATION:")
    if main_engines and ai_engines:
        print(f"  ✅ Focus analytics on main V7P3R engines")
        print(f"  ✅ Separate experimental AI engines into different category")  
        print(f"  ✅ Update transform layer to distinguish properly")
    elif main_engines:
        print(f"  ✅ Only main V7P3R engines found - proceed with analysis")
    elif ai_engines:
        print(f"  ⚠️  Only experimental AI engines found - may want to collect main engine data")
    else:
        print(f"  ❌ No V7P3R engines found - check data ingestion")

if __name__ == "__main__":
    investigate_v7p3r_engines()