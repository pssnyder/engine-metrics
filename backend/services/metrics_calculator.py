import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database.models import Game, MetricsCache, SessionLocal

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculates and caches chess engine performance metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_engines = [name.lower() for name in config.get('engines', {}).get('target_engines', [])]
        self.cache_duration_hours = 1  # Cache metrics for 1 hour
        
    def _get_target_engine_games_query(self, db: Session):
        """Get base query for games between target engines only."""
        # Create conditions for target engines
        engine_conditions = []
        for engine in self.target_engines:
            engine_conditions.append(
                and_(
                    func.lower(Game.white_player).like(f'%{engine}%'),
                    func.lower(Game.black_player).like(f'%{engine}%'),
                    Game.white_player != Game.black_player  # Ensure it's not same engine
                )
            )
        
        return db.query(Game).filter(or_(*engine_conditions))
    
    def _get_engine_name_from_player(self, player_name: str) -> Optional[str]:
        """Extract engine name from player string."""
        if not player_name:
            return None
        
        player_lower = player_name.lower()
        for engine in self.target_engines:
            if engine in player_lower:
                return engine
        return None
    
    async def calculate_head_to_head_metrics(self) -> Dict[str, Any]:
        """Calculate head-to-head metrics between target engines."""
        db = SessionLocal()
        try:
            # Get all target engine games
            games_query = self._get_target_engine_games_query(db)
            games = games_query.all()
            
            logger.info(f"Calculating metrics for {len(games)} head-to-head games")
            
            # Initialize metrics structure
            metrics = {
                'total_games': len(games),
                'last_updated': datetime.utcnow().isoformat(),
                'engines': {},
                'head_to_head': {},
                'termination_analysis': {},
                'time_analysis': {},
                'recent_performance': {}
            }
            
            # Initialize engine stats
            for engine in self.target_engines:
                metrics['engines'][engine] = {
                    'total_games': 0,
                    'wins': 0,
                    'losses': 0,
                    'draws': 0,
                    'win_rate': 0.0,
                    'decisive_wins': 0,
                    'soft_losses': 0,
                    'missed_wins': 0,
                    'average_game_length': 0.0,
                    'average_time_per_move': 0.0,
                    'average_depth': 0.0
                }
            
            # Process each game
            for game in games:
                white_engine = self._get_engine_name_from_player(game.white_player)
                black_engine = self._get_engine_name_from_player(game.black_player)
                
                if not white_engine or not black_engine or white_engine == black_engine:
                    continue
                
                # Update game counts
                metrics['engines'][white_engine]['total_games'] += 1
                metrics['engines'][black_engine]['total_games'] += 1
                
                # Process result
                if game.result == '1-0':  # White wins
                    metrics['engines'][white_engine]['wins'] += 1
                    metrics['engines'][black_engine]['losses'] += 1
                elif game.result == '0-1':  # Black wins
                    metrics['engines'][black_engine]['wins'] += 1
                    metrics['engines'][white_engine]['losses'] += 1
                elif game.result == '1/2-1/2':  # Draw
                    metrics['engines'][white_engine]['draws'] += 1
                    metrics['engines'][black_engine]['draws'] += 1
                
                # Process custom classifications
                if game.is_decisive_win:
                    winner_engine = white_engine if game.result == '1-0' else black_engine
                    if winner_engine:
                        metrics['engines'][winner_engine]['decisive_wins'] += 1
                
                if game.is_soft_loss:
                    loser_engine = black_engine if game.result == '1-0' else white_engine
                    if loser_engine:
                        metrics['engines'][loser_engine]['soft_losses'] += 1
                
                if game.is_missed_win:
                    # Missed wins can apply to both engines in different scenarios
                    if game.result == '1/2-1/2':  # Draw
                        # Both engines could have missed wins in a draw
                        metrics['engines'][white_engine]['missed_wins'] += 0.5
                        metrics['engines'][black_engine]['missed_wins'] += 0.5
                    else:
                        # The losing engine had a missed win
                        loser_engine = black_engine if game.result == '1-0' else white_engine
                        if loser_engine:
                            metrics['engines'][loser_engine]['missed_wins'] += 1
                
                # Accumulate time and depth data
                if game.white_avg_time and white_engine:
                    current_avg = metrics['engines'][white_engine]['average_time_per_move']
                    games_count = metrics['engines'][white_engine]['total_games']
                    metrics['engines'][white_engine]['average_time_per_move'] = \
                        ((current_avg * (games_count - 1)) + game.white_avg_time) / games_count
                
                if game.black_avg_time and black_engine:
                    current_avg = metrics['engines'][black_engine]['average_time_per_move']
                    games_count = metrics['engines'][black_engine]['total_games']
                    metrics['engines'][black_engine]['average_time_per_move'] = \
                        ((current_avg * (games_count - 1)) + game.black_avg_time) / games_count
                
                if game.white_avg_depth and white_engine:
                    current_avg = metrics['engines'][white_engine]['average_depth']
                    games_count = metrics['engines'][white_engine]['total_games']
                    metrics['engines'][white_engine]['average_depth'] = \
                        ((current_avg * (games_count - 1)) + game.white_avg_depth) / games_count
                
                if game.black_avg_depth and black_engine:
                    current_avg = metrics['engines'][black_engine]['average_depth']
                    games_count = metrics['engines'][black_engine]['total_games']
                    metrics['engines'][black_engine]['average_depth'] = \
                        ((current_avg * (games_count - 1)) + game.black_avg_depth) / games_count
            
            # Calculate win rates and other derived metrics
            for engine in self.target_engines:
                engine_stats = metrics['engines'][engine]
                total = engine_stats['total_games']
                
                if total > 0:
                    engine_stats['win_rate'] = engine_stats['wins'] / total
                    engine_stats['draw_rate'] = engine_stats['draws'] / total
                    engine_stats['loss_rate'] = engine_stats['losses'] / total
            
            # Calculate head-to-head specific metrics
            h2h_key = f"{self.target_engines[0]}_vs_{self.target_engines[1]}"
            h2h_games = [g for g in games if 
                        self._get_engine_name_from_player(g.white_player) in self.target_engines and
                        self._get_engine_name_from_player(g.black_player) in self.target_engines]
            
            metrics['head_to_head'][h2h_key] = {
                'total_games': len(h2h_games),
                'white_wins': len([g for g in h2h_games if g.result == '1-0']),
                'black_wins': len([g for g in h2h_games if g.result == '0-1']),
                'draws': len([g for g in h2h_games if g.result == '1/2-1/2']),
                'decisive_outcomes': len([g for g in h2h_games if g.is_decisive_win]),
                'soft_losses': len([g for g in h2h_games if g.is_soft_loss]),
                'missed_wins': len([g for g in h2h_games if g.is_missed_win])
            }
            
            # Calculate termination analysis
            termination_stats = {}
            for game in games:
                termination = game.termination or 'Unknown'
                if termination not in termination_stats:
                    termination_stats[termination] = 0
                termination_stats[termination] += 1
            
            metrics['termination_analysis'] = termination_stats
            
            # Recent performance (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_games = [g for g in games if g.created_at >= thirty_days_ago]
            
            metrics['recent_performance'] = {
                'games_last_30_days': len(recent_games),
                'trend_analysis': 'stable'  # Can be enhanced with trend calculation
            }
            
            return metrics
        
        finally:
            db.close()
    
    async def get_cached_metrics(self, metric_type: str = 'head_to_head') -> Optional[Dict[str, Any]]:
        """Get cached metrics if still valid."""
        db = SessionLocal()
        try:
            cache_entry = db.query(MetricsCache).filter(
                MetricsCache.metric_type == metric_type,
                MetricsCache.expires_at > datetime.utcnow()
            ).first()
            
            if cache_entry:
                import json
                return json.loads(cache_entry.data)
            
            return None
        
        finally:
            db.close()
    
    async def cache_metrics(self, metric_type: str, data: Dict[str, Any]):
        """Cache metrics data."""
        db = SessionLocal()
        try:
            import json
            
            # Remove old cache entries for this metric type
            db.query(MetricsCache).filter(MetricsCache.metric_type == metric_type).delete()
            
            # Create new cache entry
            cache_entry = MetricsCache(
                metric_type=metric_type,
                computed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=self.cache_duration_hours),
                data=json.dumps(data)
            )
            
            db.add(cache_entry)
            db.commit()
        
        finally:
            db.close()
    
    async def get_metrics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get current metrics, using cache if available."""
        if not force_refresh:
            cached = await self.get_cached_metrics()
            if cached:
                logger.debug("Returning cached metrics")
                return cached
        
        logger.info("Calculating fresh metrics...")
        metrics = await self.calculate_head_to_head_metrics()
        await self.cache_metrics('head_to_head', metrics)
        
        return metrics
    
    async def get_last_update(self) -> Optional[str]:
        """Get timestamp of last metrics update."""
        db = SessionLocal()
        try:
            cache_entry = db.query(MetricsCache).filter(
                MetricsCache.metric_type == 'head_to_head'
            ).order_by(MetricsCache.computed_at.desc()).first()
            
            return cache_entry.computed_at.isoformat() if cache_entry else None
        
        finally:
            db.close()
    
    async def get_total_games(self) -> int:
        """Get total number of games in database."""
        db = SessionLocal()
        try:
            return self._get_target_engine_games_query(db).count()
        finally:
            db.close()
    
    async def get_game_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent game history."""
        db = SessionLocal()
        try:
            games = self._get_target_engine_games_query(db)\
                      .order_by(Game.created_at.desc())\
                      .limit(limit)\
                      .all()
            
            return [
                {
                    'id': game.id,
                    'date': game.date,
                    'white_player': game.white_player,
                    'black_player': game.black_player,
                    'result': game.result,
                    'termination': game.termination,
                    'total_moves': game.total_moves,
                    'is_decisive_win': game.is_decisive_win,
                    'is_soft_loss': game.is_soft_loss,
                    'is_missed_win': game.is_missed_win,
                    'created_at': game.created_at.isoformat()
                }
                for game in games
            ]
        
        finally:
            db.close()
