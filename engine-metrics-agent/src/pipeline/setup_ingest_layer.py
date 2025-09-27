#!/usr/bin/env python3
"""
Setup script for Ingest Layer - Chess Engine Metrics Pipeline
Initializes BigQuery dataset, tables, and validates configuration
"""

import os
import sys
import json
import logging
from pathlib import Path

def setup_logging():
    """Setup basic logging for the setup process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - Setup - %(levelname)s - %(message)s'
    )

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'google.cloud.storage',
        'google.cloud.bigquery',
        'pandas',
        'chess'  # python-chess
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            logging.info(f"✓ Package available: {package}")
        except ImportError:
            missing_packages.append(package)
            logging.warning(f"✗ Package missing: {package}")
    
    if missing_packages:
        logging.error("Missing required packages. Install with:")
        logging.error("pip install -r requirements_ingest_layer.txt")
        return False
    
    return True

def validate_config():
    """Validate ingest layer configuration"""
    config_path = Path(__file__).parent / "ingest_layer_config.json"
    if not config_path.exists():
        logging.error(f"Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required configuration sections
        required_sections = ['storage', 'bigquery', 'processing']
        for section in required_sections:
            if section not in config.get('ingest_layer_config', {}):
                logging.error(f"Missing configuration section: {section}")
                return False
        
        ingest_config = config['ingest_layer_config']
        
        # Validate storage config
        if not ingest_config['storage']['bucket_name']:
            logging.error("Storage bucket name not configured")
            return False
        
        # Validate BigQuery config
        if not ingest_config['bigquery']['project_id']:
            logging.error("BigQuery project ID not configured")
            return False
        
        logging.info("✓ Configuration validated successfully")
        return True
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration: {e}")
        return False
    except Exception as e:
        logging.error(f"Error validating configuration: {e}")
        return False

def setup_bigquery():
    """Setup BigQuery dataset and tables"""
    try:
        from google.cloud import bigquery
        from ingest_layer import BigQueryManager
        
        # Load config
        config_path = Path(__file__).parent / "ingest_layer_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        ingest_config = config['ingest_layer_config']
        
        # Initialize BigQuery manager (will create dataset and tables)
        bq_manager = BigQueryManager(
            project_id=ingest_config['bigquery']['project_id'],
            dataset_name=ingest_config['bigquery']['dataset_name']
        )
        
        logging.info("✓ BigQuery dataset and tables initialized")
        return True
        
    except Exception as e:
        logging.error(f"Error setting up BigQuery: {e}")
        return False

def test_bucket_access():
    """Test access to the Cloud Storage bucket"""
    try:
        from google.cloud import storage
        
        # Load config
        config_path = Path(__file__).parent / "ingest_layer_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        bucket_name = config['ingest_layer_config']['storage']['bucket_name']
        
        # Test bucket access
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # List first few objects to test access
        blobs = list(bucket.list_blobs(max_results=5))
        logging.info(f"✓ Bucket access verified - found {len(blobs)} sample files")
        
        return True
        
    except Exception as e:
        logging.error(f"Error accessing bucket: {e}")
        return False

def create_service_script():
    """Create a service runner script"""
    runner_content = '''#!/usr/bin/env python3
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
'''
    
    runner_path = Path(__file__).parent / "run_ingest_layer.py"
    with open(runner_path, 'w') as f:
        f.write(runner_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(runner_path, 0o755)
    
    logging.info(f"Created service runner: {runner_path}")

def main():
    """Main setup function"""
    setup_logging()
    logging.info("=== Ingest Layer Setup ===")
    
    # Run validation steps
    if not check_dependencies():
        logging.error("Dependency check failed")
        return 1
    
    if not validate_config():
        logging.error("Configuration validation failed")
        return 1
    
    if not test_bucket_access():
        logging.error("Bucket access test failed")
        return 1
    
    if not setup_bigquery():
        logging.error("BigQuery setup failed")
        return 1
    
    # Create service runner
    create_service_script()
    
    logging.info("=== Setup Complete ===")
    logging.info("Next steps:")
    logging.info("1. Verify your data is in the Cloud Storage bucket")
    logging.info("2. Run: python run_ingest_layer.py")
    logging.info("3. Choose option 1 for initial batch ingestion")
    logging.info("4. Choose option 2 for continuous monitoring")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())