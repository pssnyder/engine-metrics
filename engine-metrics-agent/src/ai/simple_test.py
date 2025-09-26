#!/usr/bin/env python3
"""
Simple health check for AI service
"""

import requests
import json
import time

def test_health():
    try:
        print("🏥 Testing AI service health...")
        response = requests.get("http://localhost:5002/", timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service is healthy!")
            print(f"   Service: {data.get('service', 'Unknown')}")
            print(f"   AI Available: {data.get('ai_available', False)}")
            return True
        else:
            print(f"❌ Service returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to AI service")
        print("💡 Make sure the service is running on port 5002")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Wait a bit for service to be ready
    print("⏳ Waiting 3 seconds for service to be ready...")
    time.sleep(3)
    
    success = test_health()
    
    if success:
        print("🎉 AI service is working!")
    else:
        print("⚠️ AI service test failed")