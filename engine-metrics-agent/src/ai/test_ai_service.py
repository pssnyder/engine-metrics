#!/usr/bin/env python3
"""
Test the AI service endpoints and functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:5002"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_storage_list():
    """Test storage file listing"""
    print("\n📁 Testing storage file listing...")
    try:
        response = requests.get(f"{BASE_URL}/api/storage/list")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Found {data.get('count', 0)} files:")
        for file in data.get('files', [])[:10]:  # Show first 10
            print(f"   - {file}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Storage list failed: {e}")
        return False

def test_auto_ingest():
    """Test automatic data ingestion from storage"""
    print("\n🤖 Testing auto-ingest from storage...")
    try:
        payload = {"prefix": "analysis_results/"}
        response = requests.post(f"{BASE_URL}/api/storage/ingest", json=payload)
        print(f"Status: {response.status_code}")
        data = response.json()
        if data.get('success'):
            result = data.get('result', {})
            print(f"Processed: {result.get('processed', 0)} files")
            print(f"Errors: {result.get('errors', 0)} files")
            print(f"Skipped: {result.get('skipped', 0)} files")
            
            # Show details
            for detail in result.get('details', [])[:5]:
                print(f"   - {detail}")
        else:
            print(f"❌ Auto-ingest failed: {data.get('error')}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Auto-ingest failed: {e}")
        return False

def test_query():
    """Test AI query processing"""
    print("\n🤔 Testing AI query processing...")
    try:
        queries = [
            "How is V7P3R performing?",
            "What engines do we have data for?",
            "Which engine performs best?",
            "Compare SlowMate vs V7P3R"
        ]
        
        for query in queries:
            print(f"\n💭 Query: '{query}'")
            payload = {"query": query, "user_id": "test_user"}
            response = requests.post(f"{BASE_URL}/api/query", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data.get('response', {})
                    print(f"✅ Answer: {result.get('answer', 'No answer')[:200]}...")
                    print(f"   Confidence: {result.get('confidence', 0)}")
                else:
                    print(f"❌ Query failed: {data.get('error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
            
            time.sleep(1)  # Rate limiting
        
        return True
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False

def test_performance_summary():
    """Test performance summary endpoint"""
    print("\n📊 Testing performance summary...")
    try:
        response = requests.get(f"{BASE_URL}/api/performance")
        print(f"Status: {response.status_code}")
        data = response.json()
        if data.get('success'):
            summary = data.get('data', {})
            print(f"Total games analyzed: {summary.get('total_games_analyzed', 0)}")
            engines = summary.get('engines', {})
            print(f"Engines tracked: {len(engines)}")
            for engine, stats in engines.items():
                print(f"   - {engine}: {stats.get('win_rate', 0)}% win rate")
        else:
            print(f"❌ Performance summary failed: {data.get('error')}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Performance summary failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Chess Engine Metrics AI Service")
    print("=" * 50)
    
    # Wait for service to be ready
    print("⏳ Waiting for service to be ready...")
    time.sleep(3)
    
    tests = [
        ("Health Check", test_health),
        ("Storage Listing", test_storage_list),
        ("Auto-Ingest", test_auto_ingest),
        ("Performance Summary", test_performance_summary),
        ("AI Query Processing", test_query)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        results[test_name] = test_func()
    
    print(f"\n{'='*50}")
    print("🎯 Test Results Summary:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\n🏆 Overall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! Your AI service is working perfectly!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")