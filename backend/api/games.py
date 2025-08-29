from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging

from services.pgn_processor import PGNProcessor
from services.metrics_calculator import MetricsCalculator
from database.models import get_db, Game
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected from main.py
metrics_calculator: Optional[MetricsCalculator] = None

def get_metrics_calculator():
    """Get the global metrics calculator instance."""
    if metrics_calculator is None:
        raise HTTPException(status_code=503, detail="Metrics calculator not initialized")
    return metrics_calculator

@router.get("/recent")
async def get_recent_games(
    limit: int = Query(50, description="Number of recent games to return", ge=1, le=200),
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get recent games."""
    try:
        games = await calculator.get_game_history(limit=limit)
        return {
            'games': games,
            'count': len(games)
        }
    except Exception as e:
        logger.error(f"Error getting recent games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_games(
    white_player: Optional[str] = Query(None, description="Filter by white player name"),
    black_player: Optional[str] = Query(None, description="Filter by black player name"),
    result: Optional[str] = Query(None, description="Filter by result (1-0, 0-1, 1/2-1/2)"),
    termination: Optional[str] = Query(None, description="Filter by termination type"),
    is_decisive_win: Optional[bool] = Query(None, description="Filter by decisive wins"),
    is_soft_loss: Optional[bool] = Query(None, description="Filter by soft losses"),
    is_missed_win: Optional[bool] = Query(None, description="Filter by missed wins"),
    limit: int = Query(100, description="Number of games to return", ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Search games with various filters."""
    try:
        query = db.query(Game)
        
        # Apply filters
        if white_player:
            query = query.filter(Game.white_player.ilike(f'%{white_player}%'))
        
        if black_player:
            query = query.filter(Game.black_player.ilike(f'%{black_player}%'))
        
        if result:
            query = query.filter(Game.result == result)
        
        if termination:
            query = query.filter(Game.termination.ilike(f'%{termination}%'))
        
        if is_decisive_win is not None:
            query = query.filter(Game.is_decisive_win == is_decisive_win)
        
        if is_soft_loss is not None:
            query = query.filter(Game.is_soft_loss == is_soft_loss)
        
        if is_missed_win is not None:
            query = query.filter(Game.is_missed_win == is_missed_win)
        
        # Get results
        games = query.order_by(Game.created_at.desc()).limit(limit).all()
        
        return {
            'games': [
                {
                    'id': game.id,
                    'date': game.date,
                    'white_player': game.white_player,
                    'black_player': game.black_player,
                    'result': game.result,
                    'termination': game.termination,
                    'total_moves': game.total_moves,
                    'time_control': game.time_control,
                    'is_decisive_win': game.is_decisive_win,
                    'is_soft_loss': game.is_soft_loss,
                    'is_missed_win': game.is_missed_win,
                    'classification_reason': game.classification_reason,
                    'white_avg_time': game.white_avg_time,
                    'black_avg_time': game.black_avg_time,
                    'white_avg_depth': game.white_avg_depth,
                    'black_avg_depth': game.black_avg_depth,
                    'created_at': game.created_at.isoformat()
                }
                for game in games
            ],
            'count': len(games),
            'filters_applied': {
                'white_player': white_player,
                'black_player': black_player,
                'result': result,
                'termination': termination,
                'is_decisive_win': is_decisive_win,
                'is_soft_loss': is_soft_loss,
                'is_missed_win': is_missed_win
            }
        }
    
    except Exception as e:
        logger.error(f"Error searching games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{game_id}")
async def get_game_details(
    game_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific game."""
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        
        if not game:
            raise HTTPException(status_code=404, detail=f"Game with ID {game_id} not found")
        
        return {
            'id': game.id,
            'file_path': game.file_path,
            'event': game.event,
            'site': game.site,
            'date': game.date,
            'round': game.round,
            'white_player': game.white_player,
            'black_player': game.black_player,
            'result': game.result,
            'termination': game.termination,
            'time_control': game.time_control,
            'total_moves': game.total_moves,
            'game_length_seconds': game.game_length_seconds,
            'white_engine_version': game.white_engine_version,
            'black_engine_version': game.black_engine_version,
            'white_avg_time': game.white_avg_time,
            'black_avg_time': game.black_avg_time,
            'white_avg_depth': game.white_avg_depth,
            'black_avg_depth': game.black_avg_depth,
            'final_material_difference': game.final_material_difference,
            'max_white_advantage': game.max_white_advantage,
            'max_black_advantage': game.max_black_advantage,
            'is_decisive_win': game.is_decisive_win,
            'is_soft_loss': game.is_soft_loss,
            'is_missed_win': game.is_missed_win,
            'classification_reason': game.classification_reason,
            'pgn_content': game.pgn_content,
            'processed_at': game.processed_at.isoformat() if game.processed_at else None,
            'created_at': game.created_at.isoformat(),
            'updated_at': game.updated_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting game details for ID {game_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview")
async def get_games_overview(db: Session = Depends(get_db)):
    """Get overview statistics about all games."""
    try:
        from sqlalchemy import func
        
        total_games = db.query(Game).count()
        decisive_wins = db.query(Game).filter(Game.is_decisive_win == True).count()
        soft_losses = db.query(Game).filter(Game.is_soft_loss == True).count()
        missed_wins = db.query(Game).filter(Game.is_missed_win == True).count()
        
        # Result distribution
        results = db.query(Game.result, func.count(Game.result))\
                   .group_by(Game.result)\
                   .all()
        
        result_distribution = {result: count for result, count in results}
        
        # Termination distribution
        terminations = db.query(Game.termination, func.count(Game.termination))\
                       .group_by(Game.termination)\
                       .all()
        
        termination_distribution = {term: count for term, count in terminations}
        
        return {
            'total_games': total_games,
            'decisive_wins': decisive_wins,
            'soft_losses': soft_losses,
            'missed_wins': missed_wins,
            'result_distribution': result_distribution,
            'termination_distribution': termination_distribution,
            'classification_percentages': {
                'decisive_win_rate': (decisive_wins / total_games * 100) if total_games > 0 else 0,
                'soft_loss_rate': (soft_losses / total_games * 100) if total_games > 0 else 0,
                'missed_win_rate': (missed_wins / total_games * 100) if total_games > 0 else 0
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting games overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
