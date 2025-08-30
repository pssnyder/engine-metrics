"""
Metrics Calculator for Chess Engine Tournament Analysis
Calculates head-to-head statistics, engine performance, and tournament insights.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add database path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from database.models import Game, ProcessingLog, MetricsCache, async_session
except ImportError:
    # Fallback for testing
    Game = None
    MetricsCache = None
    async_session = None

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculates various metrics from tournament game data."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.target_engines = config.get('engines', {}).get('target_engines', ['v7p3r', 'slowmate'])
        self.cache_duration = timedelta(minutes=5)  # Cache metrics for 5 minutes
        
    async def get_metrics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive tournament metrics."""
        try:
            # Check cache first
            if not force_refresh:
                cached_metrics = await self._get_cached_metrics('comprehensive')
                if cached_metrics:
                    return cached_metrics
            
            # Calculate fresh metrics
            metrics = await self._calculate_comprehensive_metrics()
            
            # Cache the results
            await self._cache_metrics('comprehensive', metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return self._get_fallback_metrics()
    
    async def _calculate_comprehensive_metrics(self) -> Dict[str, Any]:
        """Calculate all metrics from database."""
        if not async_session or not Game:
            return self._get_fallback_metrics()
        
        try:
            async with async_session() as session:
                from sqlalchemy import select, func, and_, or_
                
                # Get all games
                all_games_result = await session.execute(
                    select(Game).order_by(Game.date.desc())
                )
                all_games = list(all_games_result.scalars())
                
                # Calculate head-to-head between target engines
                head_to_head = await self._calculate_head_to_head(all_games)
                
                # Calculate individual engine stats
                engine_stats = await self._calculate_engine_stats(all_games)
                
                # Calculate recent activity
                recent_activity = await self._calculate_recent_activity(all_games)
                
                # Calculate tournament breakdown
                tournament_breakdown = await self._calculate_tournament_breakdown(all_games)
                
                # Calculate time-based analysis
                time_analysis = await self._calculate_time_analysis(all_games)
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'total_games': len(all_games),
                    'head_to_head': head_to_head,
                    'engines': engine_stats,
                    'recent_activity': recent_activity,
                    'tournaments': tournament_breakdown,
                    'time_analysis': time_analysis,
                    'data_freshness': 'live'
                }
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error in comprehensive metrics calculation: {e}")
            return self._get_fallback_metrics()
    
    async def _calculate_head_to_head(self, games: List) -> Dict[str, Any]:
        """Calculate head-to-head statistics between target engines."""
        try:
            # Find games between target engines
            target_games = []
            
            for game in games:
                white_lower = game.white_engine.lower()
                black_lower = game.black_engine.lower()
                
                # Check if both engines are target engines
                white_is_target = any(target.lower() in white_lower for target in self.target_engines)
                black_is_target = any(target.lower() in black_lower for target in self.target_engines)
                
                if white_is_target and black_is_target:
                    target_games.append(game)
            
            if not target_games:
                return {
                    'total_games': 0,
                    'v7p3r_wins': 0,
                    'slowmate_wins': 0,
                    'draws': 0,
                    'v7p3r_win_rate': 0.0,
                    'slowmate_win_rate': 0.0,
                    'message': 'No head-to-head games found between target engines'
                }
            
            # Count results
            v7p3r_wins = 0
            slowmate_wins = 0
            draws = 0
            
            for game in target_games:
                white_lower = game.white_engine.lower()
                black_lower = game.black_engine.lower()
                result = game.result
                
                # Determine which engine is which
                white_is_v7p3r = 'v7p3r' in white_lower
                white_is_slowmate = 'slowmate' in white_lower
                
                if result == '1-0':  # White wins
                    if white_is_v7p3r:
                        v7p3r_wins += 1
                    elif white_is_slowmate:
                        slowmate_wins += 1
                elif result == '0-1':  # Black wins
                    if white_is_v7p3r:
                        slowmate_wins += 1
                    elif white_is_slowmate:
                        v7p3r_wins += 1
                elif result == '1/2-1/2':  # Draw
                    draws += 1
            
            total_games = len(target_games)
            
            # Calculate win rates
            v7p3r_win_rate = (v7p3r_wins / total_games * 100) if total_games > 0 else 0
            slowmate_win_rate = (slowmate_wins / total_games * 100) if total_games > 0 else 0
            
            return {
                'total_games': total_games,
                'v7p3r_wins': v7p3r_wins,
                'slowmate_wins': slowmate_wins,
                'draws': draws,
                'v7p3r_win_rate': round(v7p3r_win_rate, 1),
                'slowmate_win_rate': round(slowmate_win_rate, 1),
                'draw_rate': round((draws / total_games * 100) if total_games > 0 else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating head-to-head: {e}")
            return {'error': str(e)}
    
    async def _calculate_engine_stats(self, games: List) -> Dict[str, Any]:
        """Calculate statistics for individual engines."""
        try:
            engine_stats = defaultdict(lambda: {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'win_rate': 0.0,
                'avg_game_time': 0.0,
                'total_time': 0.0,
                'games_as_white': 0,
                'games_as_black': 0,
                'white_win_rate': 0.0,
                'black_win_rate': 0.0
            })
            
            for game in games:
                white_engine = game.white_engine
                black_engine = game.black_engine
                result = game.result
                
                # Update white engine stats
                stats = engine_stats[white_engine]
                stats['total_games'] += 1
                stats['games_as_white'] += 1
                
                if result == '1-0':
                    stats['wins'] += 1
                elif result == '0-1':
                    stats['losses'] += 1
                elif result == '1/2-1/2':
                    stats['draws'] += 1
                
                # Add time if available
                if game.white_time:
                    stats['total_time'] += game.white_time
                
                # Update black engine stats
                stats = engine_stats[black_engine]
                stats['total_games'] += 1
                stats['games_as_black'] += 1
                
                if result == '0-1':
                    stats['wins'] += 1
                elif result == '1-0':
                    stats['losses'] += 1
                elif result == '1/2-1/2':
                    stats['draws'] += 1
                
                # Add time if available
                if game.black_time:
                    stats['total_time'] += game.black_time
            
            # Calculate derived statistics
            for engine, stats in engine_stats.items():
                total = stats['total_games']
                if total > 0:
                    stats['win_rate'] = round((stats['wins'] / total) * 100, 1)
                    stats['avg_game_time'] = round(stats['total_time'] / total, 1) if stats['total_time'] > 0 else 0
                    
                    # Calculate color-specific win rates
                    white_games = stats['games_as_white']
                    black_games = stats['games_as_black']
                    
                    if white_games > 0:
                        white_wins = sum(1 for game in games 
                                       if game.white_engine == engine and game.result == '1-0')
                        stats['white_win_rate'] = round((white_wins / white_games) * 100, 1)
                    
                    if black_games > 0:
                        black_wins = sum(1 for game in games 
                                       if game.black_engine == engine and game.result == '0-1')
                        stats['black_win_rate'] = round((black_wins / black_games) * 100, 1)
            
            return dict(engine_stats)
            
        except Exception as e:
            logger.error(f"Error calculating engine stats: {e}")
            return {}
    
    async def _calculate_recent_activity(self, games: List) -> List[Dict[str, Any]]:
        """Calculate recent tournament activity."""
        try:
            # Group games by tournament and date
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_games = [game for game in games if game.date >= recent_cutoff]
            
            # Group by tournament
            tournament_activity = defaultdict(list)
            for game in recent_games:
                tournament_activity[game.tournament_id].append(game)
            
            activity = []
            for tournament_id, tournament_games in tournament_activity.items():
                latest_game = max(tournament_games, key=lambda g: g.date)
                
                activity.append({
                    'tournament': tournament_id,
                    'games_count': len(tournament_games),
                    'latest_game': latest_game.date.isoformat(),
                    'status': 'recent'
                })
            
            # Sort by latest activity
            activity.sort(key=lambda x: x['latest_game'], reverse=True)
            
            return activity[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error calculating recent activity: {e}")
            return []
    
    async def _calculate_tournament_breakdown(self, games: List) -> Dict[str, Any]:
        """Calculate tournament-wise breakdown."""
        try:
            tournament_stats = {}
            
            for game in games:
                tournament = game.tournament_id
                
                if tournament not in tournament_stats:
                    tournament_stats[tournament] = {
                        'total_games': 0,
                        'date_range': {'start': None, 'end': None},
                        'engines': set(),
                        'results': {'wins': 0, 'losses': 0, 'draws': 0}
                    }
                
                stats = tournament_stats[tournament]
                stats['total_games'] += 1
                stats['engines'].add(game.white_engine)
                stats['engines'].add(game.black_engine)
                
                # Update date range
                if stats['date_range']['start'] is None or game.date < stats['date_range']['start']:
                    stats['date_range']['start'] = game.date
                if stats['date_range']['end'] is None or game.date > stats['date_range']['end']:
                    stats['date_range']['end'] = game.date
                
                # Count results
                if game.result == '1-0' or game.result == '0-1':
                    stats['results']['wins'] += 1
                elif game.result == '1/2-1/2':
                    stats['results']['draws'] += 1
                else:
                    stats['results']['losses'] += 1
            
            # Convert to serializable format
            breakdown = {}
            for tournament, stats in tournament_stats.items():
                breakdown[tournament] = {
                    'total_games': stats['total_games'],
                    'engines_count': len(stats['engines']),
                    'engines': list(stats['engines']),
                    'start_date': stats['date_range']['start'].isoformat() if stats['date_range']['start'] else None,
                    'end_date': stats['date_range']['end'].isoformat() if stats['date_range']['end'] else None,
                    'results': stats['results']
                }
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error calculating tournament breakdown: {e}")
            return {}
    
    async def _calculate_time_analysis(self, games: List) -> Dict[str, Any]:
        """Calculate time-based analysis."""
        try:
            # Games by day of week
            day_counts = defaultdict(int)
            
            # Games by time control
            time_control_counts = defaultdict(int)
            
            # Game length analysis
            move_counts = []
            
            for game in games:
                # Day of week
                day_name = game.date.strftime('%A')
                day_counts[day_name] += 1
                
                # Time control
                time_control = game.time_control or 'Unknown'
                time_control_counts[time_control] += 1
                
                # Move count
                if game.move_count:
                    move_counts.append(game.move_count)
            
            # Calculate average game length
            avg_moves = sum(move_counts) / len(move_counts) if move_counts else 0
            
            return {
                'games_by_day': dict(day_counts),
                'time_controls': dict(time_control_counts),
                'average_game_length': round(avg_moves, 1),
                'total_analyzed_games': len(games)
            }
            
        except Exception as e:
            logger.error(f"Error calculating time analysis: {e}")
            return {}
    
    async def _get_cached_metrics(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached metrics if still valid."""
        if not async_session or not MetricsCache:
            return None
        
        try:
            async with async_session() as session:
                from sqlalchemy import select
                
                stmt = select(MetricsCache).where(
                    MetricsCache.cache_key == cache_key
                ).where(
                    MetricsCache.expires_at > datetime.now()
                )
                
                result = await session.execute(stmt)
                cached = result.scalar_one_or_none()
                
                if cached:
                    return json.loads(cached.data)
                
        except Exception as e:
            logger.error(f"Error retrieving cached metrics: {e}")
        
        return None
    
    async def _cache_metrics(self, cache_key: str, metrics: Dict[str, Any]):
        """Cache metrics for future use."""
        if not async_session or not MetricsCache:
            return
        
        try:
            async with async_session() as session:
                from sqlalchemy import select
                
                # Remove existing cache entry
                existing_stmt = select(MetricsCache).where(MetricsCache.cache_key == cache_key)
                existing_result = await session.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    await session.delete(existing)
                
                # Create new cache entry
                cache_entry = MetricsCache(
                    cache_key=cache_key,
                    data=json.dumps(metrics),
                    expires_at=datetime.now() + self.cache_duration
                )
                
                session.add(cache_entry)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error caching metrics: {e}")
    
    def _get_fallback_metrics(self) -> Dict[str, Any]:
        """Get fallback metrics when database is unavailable."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_games': 0,
            'head_to_head': {
                'total_games': 0,
                'v7p3r_wins': 0,
                'slowmate_wins': 0,
                'draws': 0,
                'v7p3r_win_rate': 0.0,
                'slowmate_win_rate': 0.0,
                'message': 'Database not available'
            },
            'engines': {},
            'recent_activity': [],
            'tournaments': {},
            'time_analysis': {},
            'data_freshness': 'fallback'
        }

if __name__ == "__main__":
    # Test the metrics calculator
    async def test_calculator():
        config = {
            'engines': {
                'target_engines': ['v7p3r', 'slowmate']
            }
        }
        
        calculator = MetricsCalculator(config)
        print("✅ Metrics Calculator initialized successfully")
        
        metrics = await calculator.get_metrics()
        print(f"Sample metrics: {metrics}")
    
    asyncio.run(test_calculator())
