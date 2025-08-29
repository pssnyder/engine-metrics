from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging

from services.metrics_calculator import MetricsCalculator
from database.models import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# This will be injected from main.py
metrics_calculator: Optional[MetricsCalculator] = None

def get_metrics_calculator():
    """Get the global metrics calculator instance."""
    if metrics_calculator is None:
        raise HTTPException(status_code=503, detail="Metrics calculator not initialized")
    return metrics_calculator

@router.get("/summary")
async def get_metrics_summary(
    force_refresh: bool = Query(False, description="Force refresh of cached metrics"),
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get summary metrics for engine performance."""
    try:
        metrics = await calculator.get_metrics(force_refresh=force_refresh)
        return metrics
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/engines/{engine_name}")
async def get_engine_metrics(
    engine_name: str,
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get detailed metrics for a specific engine."""
    try:
        metrics = await calculator.get_metrics()
        
        engine_name_lower = engine_name.lower()
        if engine_name_lower not in metrics.get('engines', {}):
            raise HTTPException(status_code=404, detail=f"Engine '{engine_name}' not found")
        
        return {
            'engine_name': engine_name,
            'metrics': metrics['engines'][engine_name_lower],
            'last_updated': metrics.get('last_updated')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting engine metrics for {engine_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/head-to-head")
async def get_head_to_head_metrics(
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get head-to-head comparison metrics."""
    try:
        metrics = await calculator.get_metrics()
        return {
            'head_to_head': metrics.get('head_to_head', {}),
            'termination_analysis': metrics.get('termination_analysis', {}),
            'last_updated': metrics.get('last_updated')
        }
    except Exception as e:
        logger.error(f"Error getting head-to-head metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent-performance")
async def get_recent_performance(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get recent performance metrics."""
    try:
        metrics = await calculator.get_metrics()
        return {
            'recent_performance': metrics.get('recent_performance', {}),
            'time_analysis': metrics.get('time_analysis', {}),
            'last_updated': metrics.get('last_updated')
        }
    except Exception as e:
        logger.error(f"Error getting recent performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh_metrics(
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Force refresh of all metrics."""
    try:
        logger.info("Manual metrics refresh requested")
        metrics = await calculator.get_metrics(force_refresh=True)
        return {
            'message': 'Metrics refreshed successfully',
            'total_games': metrics.get('total_games', 0),
            'last_updated': metrics.get('last_updated')
        }
    except Exception as e:
        logger.error(f"Error refreshing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
