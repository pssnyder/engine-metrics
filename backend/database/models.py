from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Game(Base):
    """Database model for chess games."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Game identification
    file_path = Column(String, nullable=False)
    file_hash = Column(String, unique=True, index=True)  # To prevent duplicates
    
    # Game metadata
    event = Column(String)
    site = Column(String)
    date = Column(String)
    round = Column(String)
    
    # Players
    white_player = Column(String, nullable=False, index=True)
    black_player = Column(String, nullable=False, index=True)
    
    # Result
    result = Column(String, nullable=False)  # 1-0, 0-1, 1/2-1/2
    termination = Column(String)  # Normal, Time forfeit, Abandoned, etc.
    
    # Time control
    time_control = Column(String)
    
    # Game analysis
    total_moves = Column(Integer)
    game_length_seconds = Column(Float)
    
    # Engine-specific data
    white_engine_version = Column(String)
    black_engine_version = Column(String)
    white_avg_time = Column(Float)
    black_avg_time = Column(Float)
    white_avg_depth = Column(Float)
    black_avg_depth = Column(Float)
    
    # Material tracking for missed wins analysis
    final_material_difference = Column(Float)  # Positive = white advantage
    max_white_advantage = Column(Float)
    max_black_advantage = Column(Float)
    
    # Custom classifications
    is_decisive_win = Column(Boolean, default=False)
    is_soft_loss = Column(Boolean, default=False)
    is_missed_win = Column(Boolean, default=False)
    classification_reason = Column(Text)
    
    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    pgn_content = Column(Text)  # Store original PGN for reprocessing
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProcessingLog(Base):
    """Log of file processing activities."""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    processing_started = Column(DateTime, default=datetime.utcnow)
    processing_completed = Column(DateTime)
    status = Column(String, nullable=False)  # success, error, skipped
    games_processed = Column(Integer, default=0)
    error_message = Column(Text)
    file_size = Column(Integer)
    encoding_used = Column(String)

class MetricsCache(Base):
    """Cache for computed metrics to improve performance."""
    __tablename__ = "metrics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String, nullable=False, index=True)
    engine_filter = Column(String)  # JSON string of filter parameters
    computed_at = Column(DateTime, default=datetime.utcnow)
    data = Column(Text, nullable=False)  # JSON string of metric data
    expires_at = Column(DateTime)

# Database initialization
def get_database_url():
    """Get database URL from config or default."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml")
    try:
        import yaml
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            db_path = config.get('database', {}).get('path', './database/chess_metrics.db')
            # Convert relative path to absolute
            if not os.path.isabs(db_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                db_path = os.path.join(base_dir, db_path)
            return f"sqlite:///{db_path}"
    except Exception:
        # Fallback
        db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "database")
        os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{os.path.join(db_dir, 'chess_metrics.db')}"

# Create engine and session
engine = create_engine(get_database_url(), echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
