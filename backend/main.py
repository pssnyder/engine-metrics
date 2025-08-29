import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import yaml
import os
import sys
from typing import Dict, List, Any

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

from database.models import init_db
from services.pgn_processor import PGNProcessor
from services.metrics_calculator import MetricsCalculator
from services.file_watcher import FileWatcher
from api import games, metrics, config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
pgn_processor = None
file_watcher = None
metrics_calculator = None

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global pgn_processor, file_watcher, metrics_calculator
    
    logger.info("Starting Engine Metrics Dashboard...")
    
    # Initialize database
    await init_db()
    
    # Load configuration
    config_data = load_config()
    
    # Initialize services
    pgn_processor = PGNProcessor(config_data)
    metrics_calculator = MetricsCalculator(config_data)
    file_watcher = FileWatcher(config_data, pgn_processor)
    
    # Start file watching and batch processing
    await file_watcher.start()
    
    logger.info("Engine Metrics Dashboard started successfully!")
    
    yield
    
    # Cleanup
    if file_watcher:
        await file_watcher.stop()
    logger.info("Engine Metrics Dashboard stopped.")

# Create FastAPI app
app = FastAPI(
    title="Engine Metrics Dashboard",
    description="Chess Engine Performance Monitoring Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Load config for CORS
config_data = load_config()
cors_origins = config_data.get('server', {}).get('cors_origins', ["http://localhost:3000"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

# Inject global instances into API modules
def setup_api_dependencies():
    global pgn_processor, metrics_calculator
    games.metrics_calculator = metrics_calculator
    metrics.metrics_calculator = metrics_calculator

@app.on_event("startup")
async def startup_event():
    setup_api_dependencies()

# Inject global instances into API modules
@app.on_event("startup")
async def inject_dependencies():
    """Inject global instances into API modules."""
    global pgn_processor, file_watcher, metrics_calculator
    if metrics_calculator:
        metrics.metrics_calculator = metrics_calculator
        games.metrics_calculator = metrics_calculator

# Serve static files (React build)
static_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "pgn_processor": pgn_processor is not None,
            "file_watcher": file_watcher is not None,
            "metrics_calculator": metrics_calculator is not None
        }
    }

@app.get("/api/status")
async def get_status():
    """Get system status and statistics."""
    if not file_watcher:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    return {
        "processing_status": await file_watcher.get_status(),
        "last_update": await metrics_calculator.get_last_update() if metrics_calculator else None,
        "total_games": await metrics_calculator.get_total_games() if metrics_calculator else 0
    }

if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    server_config = config.get('server', {})
    
    uvicorn.run(
        "main:app",
        host=server_config.get('host', '0.0.0.0'),
        port=server_config.get('port', 8000),
        reload=server_config.get('debug', False)
    )
