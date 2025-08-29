#!/usr/bin/env python3
"""
Test script to verify the Engine Metrics Dashboard setup
"""

import os
import sys
import yaml
import sqlite3
from pathlib import Path

def test_configuration():
    """Test that configuration file is readable and valid."""
    print("Testing configuration...")
    
    config_path = Path("config/settings.yaml")
    if not config_path.exists():
        print("❌ Config file not found: config/settings.yaml")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        print("✅ Configuration file loaded successfully")
        
        # Check required sections
        required_sections = ['processing', 'engines', 'directories', 'server']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing required config section: {section}")
                return False
        
        print("✅ All required configuration sections present")
        return True
    
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

def test_directories():
    """Test that monitored directories exist."""
    print("\nTesting directories...")
    
    try:
        with open("config/settings.yaml", 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        directories = config.get('directories', {})
        local_paths = directories.get('local_paths', [])
        
        if not local_paths:
            print("⚠️  No local paths configured")
            return True
        
        all_good = True
        for path in local_paths:
            abs_path = Path(path).resolve()
            if abs_path.exists():
                print(f"✅ Directory exists: {path} -> {abs_path}")
            else:
                print(f"❌ Directory not found: {path} -> {abs_path}")
                all_good = False
        
        return all_good
    
    except Exception as e:
        print(f"❌ Error checking directories: {e}")
        return False

def test_database():
    """Test database creation and basic operations."""
    print("\nTesting database...")
    
    try:
        # Create database directory
        db_dir = Path("database")
        db_dir.mkdir(exist_ok=True)
        
        # Test SQLite connection
        db_path = db_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Test basic operations
        cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO test (id) VALUES (1)")
        cursor.execute("SELECT * FROM test")
        result = cursor.fetchone()
        
        conn.close()
        
        # Clean up test database
        if db_path.exists():
            db_path.unlink()
        
        print("✅ Database operations working")
        return True
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_imports():
    """Test that all required Python packages are available."""
    print("\nTesting Python imports...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'chess',
        'yaml',
        'sqlalchemy',
        'pandas',
        'watchdog',
        'chardet'
    ]
    
    all_good = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError as e:
            print(f"❌ {package}: {e}")
            all_good = False
    
    return all_good

def test_pgn_files():
    """Check for existing PGN files to process."""
    print("\nChecking for PGN files...")
    
    try:
        with open("config/settings.yaml", 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        directories = config.get('directories', {})
        local_paths = directories.get('local_paths', [])
        
        total_pgn_files = 0
        for path in local_paths:
            abs_path = Path(path).resolve()
            if abs_path.exists():
                pgn_files = list(abs_path.glob("**/*.pgn")) + list(abs_path.glob("**/*.PGN"))
                print(f"📁 {path}: {len(pgn_files)} PGN files")
                total_pgn_files += len(pgn_files)
        
        if total_pgn_files > 0:
            print(f"✅ Found {total_pgn_files} total PGN files to process")
        else:
            print("⚠️  No PGN files found - add some tournament results to start monitoring")
        
        return True
    
    except Exception as e:
        print(f"❌ Error checking PGN files: {e}")
        return False

def main():
    """Run all tests."""
    print("🏁 Engine Metrics Dashboard - Setup Test")
    print("=" * 50)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    if script_dir.name == "backend":
        os.chdir(script_dir.parent)
    
    tests = [
        test_configuration,
        test_directories,
        test_database,
        test_imports,
        test_pgn_files
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    if all(results):
        print("✅ All tests passed! Your setup is ready.")
        print("\n🚀 To start the dashboard:")
        print("   Windows: start-backend.bat")
        print("   Linux/Mac: ./start-backend.sh")
        print("\n🌐 Dashboard will be available at: http://localhost:8000")
    else:
        print("❌ Some tests failed. Please fix the issues above before starting.")
        failed_count = sum(1 for r in results if not r)
        print(f"   {failed_count} out of {len(results)} tests failed.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
