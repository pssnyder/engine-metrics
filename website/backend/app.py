"""
Main FastAPI application for the chess engine metrics backend.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yaml
from typing import Dict, Any, Optional

from database.models import init_db
from services.pgn_processor import PGNProcessor
from services.metrics_calculator import MetricsCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
config = None
pgn_processor = None
metrics_calculator = None

async def load_config():
    """Load configuration from YAML file."""
    global config
    try:
        # Use absolute path calculation
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(backend_dir)
        config_path = os.path.join(project_root, 'config', 'settings.yaml')
        
        logger.info(f"Loading config from: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded successfully from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

async def initialize_services():
    """Initialize all services."""
    global pgn_processor, metrics_calculator
    
    await load_config()
    
    # Initialize database
    await init_db()
    
    # Initialize services with config check
    if config is None:
        raise ValueError("Configuration not loaded")
    
    pgn_processor = PGNProcessor(config)
    metrics_calculator = MetricsCalculator(config)
    
    logger.info("All services initialized successfully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting up backend services...")
    await initialize_services()
    
    yield
    
    # Shutdown
    logger.info("Shutting down backend services...")

# Create FastAPI app
app = FastAPI(
    title="Chess Engine Metrics API",
    description="Backend API for chess engine tournament metrics and analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_config() -> Dict[str, Any]:
    """Dependency to get configuration."""
    if config is None:
        raise HTTPException(status_code=500, detail="Configuration not loaded")
    return config

def get_pgn_processor() -> PGNProcessor:
    """Dependency to get PGN processor."""
    if pgn_processor is None:
        raise HTTPException(status_code=500, detail="PGN processor not initialized")
    return pgn_processor

def get_metrics_calculator() -> MetricsCalculator:
    """Dependency to get metrics calculator."""
    if metrics_calculator is None:
        raise HTTPException(status_code=500, detail="Metrics calculator not initialized")
    return metrics_calculator

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Chess Engine Metrics API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "pgn_processor": pgn_processor is not None,
            "metrics_calculator": metrics_calculator is not None,
            "config": config is not None
        }
    }

@app.get("/api/metrics/comprehensive")
async def get_comprehensive_metrics(
    force_refresh: bool = False,
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get comprehensive tournament metrics."""
    try:
        metrics = await calculator.get_metrics(force_refresh=force_refresh)
        return metrics
    except Exception as e:
        logger.error(f"Error getting comprehensive metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/head-to-head")
async def get_head_to_head_metrics(
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get head-to-head metrics between target engines."""
    try:
        # Get comprehensive metrics and extract head-to-head
        metrics = await calculator.get_metrics()
        return metrics.get('head_to_head', {})
    except Exception as e:
        logger.error(f"Error getting head-to-head metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/tournaments")
async def get_tournament_metrics(
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get tournament breakdown metrics."""
    try:
        metrics = await calculator.get_metrics()
        return metrics.get('tournaments', {})
    except Exception as e:
        logger.error(f"Error getting tournament metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process/file")
async def process_pgn_file(
    file_path: str,
    processor: PGNProcessor = Depends(get_pgn_processor)
):
    """Process a single PGN file."""
    try:
        result = await processor.process_file(file_path)
        return result
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process/batch")
async def process_batch(
    processor: PGNProcessor = Depends(get_pgn_processor)
):
    """Process all PGN files in configured directories."""
    try:
        result = await processor.process_batch()
        return result
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status(
    processor: PGNProcessor = Depends(get_pgn_processor),
    calculator: MetricsCalculator = Depends(get_metrics_calculator)
):
    """Get overall system status."""
    try:
        # Get processing status
        processing_stats = await processor.get_processing_stats()
        
        # Get basic metrics info
        metrics = await calculator.get_metrics()
        
        return {
            "system_status": "operational",
            "processing": processing_stats,
            "metrics": {
                "total_games": metrics.get('total_games', 0),
                "last_updated": metrics.get('timestamp'),
                "data_freshness": metrics.get('data_freshness', 'unknown')
            }
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )
