from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import yaml
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/settings")
async def get_settings():
    """Get current configuration settings."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Don't expose sensitive information
        safe_config = {
            'processing': config.get('processing', {}),
            'engines': config.get('engines', {}),
            'directories': {
                'local_paths': config.get('directories', {}).get('local_paths', []),
                'file_patterns': config.get('directories', {}).get('file_patterns', [])
                # Don't expose network paths for security
            },
            'metrics': config.get('metrics', {}),
            'server': {
                'port': config.get('server', {}).get('port'),
                'debug': config.get('server', {}).get('debug')
            }
        }
        
        return safe_config
    
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/directories")
async def get_monitored_directories():
    """Get list of directories being monitored."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        directories_config = config.get('directories', {})
        local_paths = directories_config.get('local_paths', [])
        
        # Check which directories actually exist
        directory_status = []
        for path in local_paths:
            # Convert relative paths to absolute
            if not os.path.isabs(path):
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                abs_path = os.path.abspath(os.path.join(base_dir, path))
            else:
                abs_path = path
            
            directory_status.append({
                'path': path,
                'absolute_path': abs_path,
                'exists': os.path.exists(abs_path),
                'is_directory': os.path.isdir(abs_path) if os.path.exists(abs_path) else False
            })
        
        return {
            'monitored_directories': directory_status,
            'file_patterns': directories_config.get('file_patterns', [])
        }
    
    except Exception as e:
        logger.error(f"Error getting monitored directories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/engines")
async def get_engine_config():
    """Get engine configuration."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        engines_config = config.get('engines', {})
        
        return {
            'target_engines': engines_config.get('target_engines', []),
            'version_pattern': engines_config.get('version_pattern', ''),
        }
    
    except Exception as e:
        logger.error(f"Error getting engine config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
