#!/usr/bin/env python3
"""
Test Firebase connectivity with Application Default Credentials
"""

import os
# Clear the old service account key environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

os.environ['GOOGLE_CLOUD_PROJECT'] = 'chess-engine-metrics-agent'

try:
    from google.cloud import firestore
    from google.cloud import storage
    
    print("🔥 Testing Firebase connections...")
    
    # Test Firestore
    print("📊 Testing Firestore...")
    db = firestore.Client(project='chess-engine-metrics-agent')
    test_ref = db.collection('_test').document('connection_test')
    test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP, 'status': 'connected'}, merge=True)
    print("✅ Firestore connection successful!")
    
    # Test Storage
    print("🗄️ Testing Firebase Storage...")
    storage_client = storage.Client(project='chess-engine-metrics-agent')
    bucket = storage_client.bucket('chess-engine-metrics-agent.firebasestorage.app')
    
    if bucket.exists():
        print("✅ Firebase Storage connection successful!")
        
        # List some files
        blobs = list(bucket.list_blobs(max_results=5))
        if blobs:
            print(f"📁 Found {len(blobs)} files in storage:")
            for blob in blobs:
                print(f"   - {blob.name}")
        else:
            print("📂 Storage bucket is empty")
    else:
        print("❌ Storage bucket not found")
    
    print("\n🎉 All Firebase connections successful!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n💡 Troubleshooting:")
    print("1. Ensure you're logged in: firebase login")
    print("2. Set up ADC: gcloud auth application-default login")
    print("3. Check project: firebase use chess-engine-metrics-agent")