#!/usr/bin/env python3
"""
Setup script for Move Layer - Chess Engine Metrics Pipeline
Initializes the Move Layer service and validates configuration
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

def validate_directories(config):
    """Ensure required directories exist"""
    local_paths = config['move_layer_config']['local_paths']
    raw_data_dir = Path(local_paths['raw_data_directory'])
    
    # Create pipeline directory structure
    pipeline_dir = Path(__file__).parent
    state_dir = pipeline_dir / 'state'
    logs_dir = pipeline_dir / 'logs'
    
    dirs_to_create = [state_dir, logs_dir]
    
    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created/verified directory: {directory}")
    
    # Verify raw_data exists
    if not raw_data_dir.exists():
        logging.error(f"Raw data directory does not exist: {raw_data_dir}")
        return False
    
    logging.info(f"Raw data directory verified: {raw_data_dir}")
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'google.cloud.storage',
        'watchdog',
        'hashlib'
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
        logging.error("pip install -r requirements_move_layer.txt")
        return False
    
    return True

def validate_cloud_config(config):
    """Validate cloud storage configuration"""
    cloud_config = config['move_layer_config']['cloud_storage']
    
    bucket_name = cloud_config.get('bucket_name')
    project_id = cloud_config.get('project_id')
    
    if not bucket_name:
        logging.error("Cloud bucket name not configured")
        return False
    
    if not project_id:
        logging.error("Google Cloud project ID not configured")
        return False
    
    # Check for credentials
    credentials_path = cloud_config.get('credentials_path')
    if credentials_path and not os.path.exists(credentials_path):
        logging.warning(f"Credentials file not found: {credentials_path}")
        logging.warning("Will attempt to use default application credentials")
    
    logging.info(f"Cloud configuration validated - Bucket: {bucket_name}, Project: {project_id}")
    return True

def create_service_script():
    """Create a service runner script"""
    runner_content = '''#!/usr/bin/env python3
"""
Move Layer Service Runner
Starts the Move Layer file monitoring and upload service
"""

import sys
from pathlib import Path

# Add the pipeline directory to the Python path
pipeline_dir = Path(__file__).parent
sys.path.insert(0, str(pipeline_dir))

from move_layer import MoveLayer
import json
import logging

def main():
    # Load configuration
    config_path = pipeline_dir / "move_layer_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Initialize and start the Move Layer
    move_layer = MoveLayer(config)
    
    try:
        logging.info("Starting Move Layer service...")
        move_layer.start()
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, stopping Move Layer...")
        move_layer.stop()
    except Exception as e:
        logging.error(f"Move Layer error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    runner_path = Path(__file__).parent / "run_move_layer.py"
    with open(runner_path, 'w') as f:
        f.write(runner_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(runner_path, 0o755)
    
    logging.info(f"Created service runner: {runner_path}")

def main():
    """Main setup function"""
    setup_logging()
    logging.info("=== Move Layer Setup ===")
    
    # Load configuration
    config_path = Path(__file__).parent / "move_layer_config.json"
    if not config_path.exists():
        logging.error(f"Configuration file not found: {config_path}")
        return 1
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Run validation steps
    if not validate_directories(config):
        logging.error("Directory validation failed")
        return 1
    
    if not check_dependencies():
        logging.error("Dependency check failed")
        return 1
    
    if not validate_cloud_config(config):
        logging.error("Cloud configuration validation failed")
        return 1
    
    # Create service runner
    create_service_script()
    
    logging.info("=== Setup Complete ===")
    logging.info("Next steps:")
    logging.info("1. Configure Google Cloud credentials")
    logging.info("2. Update bucket name and project ID in move_layer_config.json")
    logging.info("3. Run: python run_move_layer.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())