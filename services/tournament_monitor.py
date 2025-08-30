"""
Tournament Monitor Service
Coordinates Arena monitoring, file processing, and real-time updates.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from arena_monitor import ArenaMonitor
from realtime_etl import RealTimeETL

logger = logging.getLogger(__name__)

class TournamentMonitorService:
    """Main service that coordinates all tournament monitoring components."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.arena_monitor: Optional[ArenaMonitor] = None
        self.etl_pipeline: Optional[RealTimeETL] = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
    
    async def start(self):
        """Start all monitoring services."""
        try:
            logger.info("Starting Tournament Monitor Service...")
            
            # Initialize ETL pipeline
            logger.info("Initializing ETL pipeline...")
            self.etl_pipeline = RealTimeETL(self.config_path)
            if not await self.etl_pipeline.initialize():
                logger.error("Failed to initialize ETL pipeline")
                return False
            
            # Initialize Arena monitor
            logger.info("Initializing Arena monitor...")
            self.arena_monitor = ArenaMonitor(self.config_path)
            if not self.arena_monitor.start():
                logger.error("Failed to start Arena monitor")
                return False
            
            self.running = True
            logger.info("Tournament Monitor Service started successfully!")
            
            # Main monitoring loop
            await self._monitor_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Tournament Monitor Service: {e}")
            return False
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting main monitoring loop...")
        
        last_file_count = 0
        
        while self.running:
            try:
                # Check for new files to process
                if self.arena_monitor:
                    arena_status = self.arena_monitor.get_status()
                    current_file_count = arena_status.get('files_processed', 0)
                    
                    # If new files were processed, trigger ETL
                    if current_file_count > last_file_count:
                        new_files_count = current_file_count - last_file_count
                        logger.info(f"Detected {new_files_count} new files, triggering ETL processing...")
                        
                        # Here we would get the actual file paths if needed
                        # For now, we'll just force a metrics refresh
                        if self.etl_pipeline:
                            await self.etl_pipeline._update_tournament_metrics([])
                        
                        last_file_count = current_file_count
                
                # Sleep before next check
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def stop(self):
        """Stop all monitoring services."""
        logger.info("Stopping Tournament Monitor Service...")
        
        self.running = False
        
        if self.arena_monitor:
            self.arena_monitor.stop()
            
        # ETL pipeline doesn't need explicit stopping
        
        logger.info("Tournament Monitor Service stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall service status."""
        arena_status = self.arena_monitor.get_status() if self.arena_monitor else {}
        etl_status = self.etl_pipeline.get_status() if self.etl_pipeline else {}
        
        return {
            'service_running': self.running,
            'arena_monitor': arena_status,
            'etl_pipeline': etl_status,
            'components_initialized': {
                'arena_monitor': self.arena_monitor is not None,
                'etl_pipeline': self.etl_pipeline is not None
            }
        }

async def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('tournament_monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Starting Chess Engine Tournament Monitor...")
    
    # Start the service
    service = TournamentMonitorService()
    
    try:
        success = await service.start()
        if not success:
            logger.error("Failed to start Tournament Monitor Service")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())
