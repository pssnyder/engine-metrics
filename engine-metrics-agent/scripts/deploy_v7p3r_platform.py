#!/usr/bin/env python3
"""
V7P3R Chess Engine Analysis - Quick Deployment Script
Deploys Firebase Functions and runs initial data processing
"""

import os
import sys
import json
import subprocess
import time
import requests
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\engine-metrics-agent")
FIREBASE_PROJECT = "chess-engine-metrics-agent"

def run_command(command, description, cwd=None):
    """Run a shell command and return success status"""
    print(f"\n🔧 {description}...")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd or PROJECT_ROOT, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"   ✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ {description} failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Exception during {description}: {e}")
        return False

def check_firebase_auth():
    """Check if Firebase is authenticated"""
    print("\n🔐 Checking Firebase Authentication...")
    
    result = subprocess.run(
        "firebase login --no-localhost", 
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    if "Logged in as" in result.stdout:
        print("   ✅ Firebase authentication verified")
        return True
    else:
        print("   ⚠️  Firebase authentication required")
        print("   Run: firebase login")
        return False

def deploy_functions():
    """Deploy Firebase Functions"""
    functions_dir = PROJECT_ROOT / "src" / "backend" / "functions"
    
    # Install dependencies
    if not run_command(
        "npm install", 
        "Installing Function dependencies", 
        cwd=functions_dir
    ):
        return False
    
    # Deploy functions
    if not run_command(
        "firebase deploy --only functions", 
        "Deploying Firebase Functions",
        cwd=PROJECT_ROOT
    ):
        return False
    
    return True

def test_functions():
    """Test deployed functions"""
    print("\n🧪 Testing deployed functions...")
    
    # Get the Firebase project URL
    project_url = f"https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net"
    
    # Test health endpoint
    try:
        response = requests.get(f"{project_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Health endpoint responding")
            data = response.json()
            print(f"   Project: {data.get('project', 'unknown')}")
        else:
            print(f"   ⚠️  Health endpoint returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Failed to test health endpoint: {e}")
    
    # Test migration status endpoint
    try:
        response = requests.get(f"{project_url}/getMigrationStatus", timeout=10)
        if response.status_code == 200:
            print("   ✅ Migration status endpoint responding")
        else:
            print(f"   ⚠️  Migration status returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Failed to test migration status: {e}")

def run_initial_elo_consolidation():
    """Trigger initial ELO consolidation"""
    print("\n📊 Running initial ELO consolidation...")
    
    project_url = f"https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net"
    
    try:
        response = requests.post(f"{project_url}/consolidateELOData", timeout=30)
        if response.status_code == 200:
            print("   ✅ ELO consolidation completed successfully")
            data = response.json()
            print(f"   Versions processed: {data.get('versionsProcessed', 0)}")
            print(f"   Analysis files: {data.get('totalAnalysisFiles', 0)}")
            print(f"   Games: {data.get('totalGames', 0)}")
        else:
            print(f"   ⚠️  ELO consolidation returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Failed to run ELO consolidation: {e}")

def main():
    """Main deployment process"""
    print("🚀 V7P3R Chess Engine Analysis - Quick Deployment")
    print("=================================================")
    
    # Set Firebase project
    if not run_command(
        f"firebase use {FIREBASE_PROJECT}", 
        "Setting Firebase project"
    ):
        print("❌ Failed to set Firebase project")
        sys.exit(1)
    
    # Check authentication
    if not check_firebase_auth():
        print("\n❌ Please authenticate with Firebase first:")
        print("   firebase login")
        sys.exit(1)
    
    # Deploy functions
    print("\n📦 Phase 1: Deploying Firebase Functions")
    if not deploy_functions():
        print("❌ Function deployment failed")
        sys.exit(1)
    
    # Wait for deployment to propagate
    print("\n⏳ Waiting for deployment to propagate...")
    time.sleep(10)
    
    # Test functions
    print("\n🧪 Phase 2: Testing Deployed Functions")
    test_functions()
    
    # Run data migration (if not already done)
    print("\n📤 Phase 3: Data Migration Check")
    print("   If you haven't run data migration yet, run:")
    print("   python scripts/migrate_v7p3r_data.py")
    
    # Run initial ELO consolidation
    print("\n📊 Phase 4: Initial ELO Consolidation")
    run_initial_elo_consolidation()
    
    # Summary
    print("\n=================================================")
    print("🏆 V7P3R Analysis Platform Deployment Summary")
    print("=================================================")
    
    print("\n✅ Deployment Completed Successfully!")
    print("\n🌐 Your V7P3R Analysis Platform is now live:")
    print(f"   Health Check: https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/health")
    print(f"   AI Processing: https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/processAI")
    print(f"   Query System: https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/query")
    print(f"   ELO Data: https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/consolidateELOData")
    
    print("\n🔄 Next Steps:")
    print("1. Run data migration: python scripts/migrate_v7p3r_data.py")
    print("2. Deploy frontend: npm run deploy:frontend")
    print("3. Set up custom domain (optional)")
    print("4. Start analyzing your V7P3R data!")
    
    print("\n💡 Quick Test Commands:")
    print("   # Test health endpoint")
    print(f'   curl "https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/health"')
    print("\n   # Test AI processing")
    print(f'   curl -X POST "https://us-central1-{FIREBASE_PROJECT}.cloudfunctions.net/processAI" \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"query":"How has V7P3R improved?"}\'')
    
    print("\n🎯 Focus Areas:")
    print("   • V7P3R ELO progression analysis")
    print("   • Stockfish victory pattern analysis")
    print("   • Development milestone correlation")
    print("   • Competitive performance tracking")
    
    print("\n🚀 Your V7P3R analysis platform is ready for action!")

if __name__ == "__main__":
    main()