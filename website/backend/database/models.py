"""
Database models for chess engine tournament analysis.
"""

import asyncio
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from pathlib import Path

Base = declarative_base()

class Game(Base):
    """Game record from PGN files."""
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    white_engine = Column(String(100), nullable=False)
    black_engine = Column(String(100), nullable=False)
    result = Column(String(10), nullable=False)  # '1-0', '0-1', '1/2-1/2'
    date = Column(DateTime, nullable=False)
    moves = Column(Text)
    time_control = Column(String(50))
    opening = Column(String(200))
    tournament_id = Column(String(100))
    round_number = Column(Integer)
    game_number = Column(Integer)
    white_time = Column(Float)
    black_time = Column(Float)
    move_count = Column(Integer)
    file_source = Column(String(500))
    file_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('file_hash', 'game_number', name='unique_game_per_file'),
    )

class ProcessingLog(Base):
    """Log of file processing operations."""
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True)
    games_processed = Column(Integer, default=0)
    processing_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    error_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)

class MetricsCache(Base):
    """Cached metrics calculations."""
    __tablename__ = 'metrics_cache'
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(200), nullable=False, unique=True)
    cache_data = Column(Text, nullable=False)  # JSON data
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///tournament_data.db"
engine = None
async_session = None

async def init_db():
    """Initialize the database."""
    global engine, async_session
    
    try:
        # Create database directory if it doesn't exist
        db_dir = Path("tournament_data.db").parent
        db_dir.mkdir(exist_ok=True)
        
        # Create async engine
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,  # Set to True for SQL debugging
            future=True
        )
        
        # Create async session factory
        from sqlalchemy.ext.asyncio import async_sessionmaker
        async_session = async_sessionmaker(
            engine, expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

async def get_session():
    """Get an async database session."""
    if async_session is None:
        await init_db()
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()

# Utility functions
async def get_db_stats():
    """Get database statistics."""
    if async_session is None:
        return None
    
    try:
        async with async_session() as session:
            # Count games
            from sqlalchemy import func
            
            games_count = await session.execute(
                func.count(Game.id).select()
            )
            games_total = games_count.scalar()
            
            # Count processed files
            files_count = await session.execute(
                func.count(ProcessingLog.id).select()
            )
            files_total = files_count.scalar()
            
            return {
                'total_games': games_total,
                'total_files': files_total,
                'database_url': DATABASE_URL
            }
            
    except Exception as e:
        print(f"Error getting database stats: {e}")
        return None

if __name__ == "__main__":
    # Test database initialization
    async def test_db():
        success = await init_db()
        if success:
            stats = await get_db_stats()
            print(f"Database stats: {stats}")
        await close_db()
    
    asyncio.run(test_db())
