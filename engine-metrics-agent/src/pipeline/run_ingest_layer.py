#!/usr/bin/env python3
"""
Ingest Layer Service Runner
Starts the Ingest Layer data ingestion service
"""

import sys
from pathlib import Path

# Add the pipeline directory to the Python path
pipeline_dir = Path(__file__).parent
sys.path.insert(0, str(pipeline_dir))

from ingest_layer import IngestLayer
import logging

def main():
    """Main function"""
    try:
        # Initialize the Ingest Layer
        ingest_layer = IngestLayer()
        
        # Get user choice for mode
        print("Chess Engine Metrics - Ingest Layer")
        print("=" * 40)
        print("1. Run initial batch ingestion")
        print("2. Start continuous monitoring")
        print("3. Run batch ingestion then start monitoring")
        print("4. Check status only")
        
        choice = input("Select mode (1-4): ").strip()
        
        if choice == "1":
            logging.info("Running initial batch ingestion...")
            stats = ingest_layer.run_initial_ingestion()
            print(f"Batch ingestion complete: {stats}")
            
        elif choice == "2":
            logging.info("Starting continuous monitoring...")
            ingest_layer.start_monitoring()
            
        elif choice == "3":
            logging.info("Running batch ingestion then starting monitoring...")
            stats = ingest_layer.run_initial_ingestion()
            print(f"Batch ingestion complete: {stats}")
            ingest_layer.start_monitoring()
            
        elif choice == "4":
            status = ingest_layer.get_status()
            print("Current Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
                
        else:
            print("Invalid choice. Exiting.")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logging.info("Service stopped by user")
        return 0
    except Exception as e:
        logging.error(f"Service error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
