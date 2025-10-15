#!/usr/bin/env python3
"""
V7P3R Lichess API Test Script
Tests connectivity and data retrieval for the v7p3r_bot
"""

import requests
import json
import sys
from datetime import datetime, timezone
import time

# Configuration
LICHESS_TOKEN = "lip_1vCANjDGz9euqYAcXwy7"
BOT_USERNAME = "v7p3r_bot"
BASE_URL = "https://lichess.org/api"

def test_lichess_connection():
    """Test basic API connectivity and authentication"""
    print("🔌 Testing Lichess API Connection...")
    
    headers = {
        "Authorization": f"Bearer {LICHESS_TOKEN}",
        "Accept": "application/json"
    }
    
    try:
        # Test basic API access
        response = requests.get(f"{BASE_URL}/account", headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_info = response.json()
            print(f"✅ API Connection successful!")
            print(f"   Account: {account_info.get('username', 'Unknown')}")
            print(f"   ID: {account_info.get('id', 'Unknown')}")
            return True
        else:
            print(f"❌ API Connection failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def get_bot_profile():
    """Get bot profile information"""
    print(f"\n👤 Fetching profile for {BOT_USERNAME}...")
    
    try:
        response = requests.get(f"{BASE_URL}/user/{BOT_USERNAME}", timeout=10)
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Bot Profile Retrieved:")
            print(f"   Username: {profile.get('username', 'N/A')}")
            print(f"   Title: {profile.get('title', 'None')}")
            print(f"   Online: {profile.get('online', False)}")
            print(f"   Created: {profile.get('createdAt', 'N/A')}")
            print(f"   Games Played: {profile.get('count', {}).get('all', 'N/A')}")
            
            # Rating information
            perfs = profile.get('perfs', {})
            print(f"   Ratings:")
            for game_type, rating_info in perfs.items():
                if isinstance(rating_info, dict) and 'rating' in rating_info:
                    print(f"     {game_type}: {rating_info['rating']} (±{rating_info.get('rd', 'N/A')})")
            
            return profile
        else:
            print(f"❌ Failed to get profile: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Profile fetch error: {str(e)}")
        return None

def get_recent_games(max_games=5):
    """Get recent games for the bot"""
    print(f"\n🎮 Fetching recent games (last {max_games})...")
    
    headers = {
        "Authorization": f"Bearer {LICHESS_TOKEN}",
        "Accept": "application/x-ndjson"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/games/user/{BOT_USERNAME}",
            headers=headers,
            params={"max": max_games, "format": "json"},
            timeout=30
        )
        
        if response.status_code == 200:
            games = []
            for line in response.text.strip().split('\n'):
                if line:
                    games.append(json.loads(line))
            
            print(f"✅ Retrieved {len(games)} recent games:")
            
            for i, game in enumerate(games, 1):
                game_id = game.get('id', 'Unknown')
                variant = game.get('variant', 'standard')
                speed = game.get('speed', 'unknown')
                status = game.get('status', 'unknown')
                
                # Get player info
                players = game.get('players', {})
                white = players.get('white', {})
                black = players.get('black', {})
                
                bot_color = 'white' if white.get('user', {}).get('name') == BOT_USERNAME else 'black'
                opponent = black.get('user', {}).get('name') if bot_color == 'white' else white.get('user', {}).get('name')
                
                # Get result
                winner = game.get('winner')
                if winner == bot_color:
                    result = "Won"
                elif winner and winner != bot_color:
                    result = "Lost"
                else:
                    result = "Draw"
                
                created_at = datetime.fromtimestamp(game.get('createdAt', 0) / 1000, timezone.utc)
                
                print(f"   {i}. {game_id} - {variant}/{speed}")
                print(f"      vs {opponent} ({bot_color}) - {result}")
                print(f"      {created_at.strftime('%Y-%m-%d %H:%M UTC')} - Status: {status}")
            
            return games
        else:
            print(f"❌ Failed to get games: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Games fetch error: {str(e)}")
        return []

def test_game_stream():
    """Test real-time game streaming capability"""
    print(f"\n📡 Testing game stream capability...")
    
    headers = {
        "Authorization": f"Bearer {LICHESS_TOKEN}",
        "Accept": "application/x-ndjson"
    }
    
    try:
        # Test streaming recent games (this would be used for real-time monitoring)
        response = requests.get(
            f"{BASE_URL}/games/user/{BOT_USERNAME}",
            headers=headers,
            params={"max": 1, "format": "json"},
            timeout=10,
            stream=True
        )
        
        if response.status_code == 200:
            print("✅ Streaming capability confirmed")
            print("   Real-time game monitoring is possible")
            return True
        else:
            print(f"❌ Streaming test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Streaming test error: {str(e)}")
        return False

def get_performance_stats():
    """Get performance statistics over time"""
    print(f"\n📊 Fetching performance statistics...")
    
    try:
        response = requests.get(f"{BASE_URL}/user/{BOT_USERNAME}/rating-history", timeout=10)
        
        if response.status_code == 200:
            rating_history = response.json()
            print(f"✅ Rating history available:")
            
            for game_type in rating_history:
                name = game_type.get('name', 'Unknown')
                points = game_type.get('points', [])
                if points:
                    latest = points[-1]
                    print(f"   {name}: Current rating ~{latest[3]} (from {len(points)} data points)")
            
            return rating_history
        else:
            print(f"❌ Failed to get rating history: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Performance stats error: {str(e)}")
        return []

def main():
    """Main test function"""
    print("=" * 60)
    print("🤖 V7P3R Lichess Bot API Test")
    print("=" * 60)
    
    # Test 1: Basic connectivity
    if not test_lichess_connection():
        print("\n❌ Basic connectivity failed. Check API token.")
        sys.exit(1)
    
    # Test 2: Bot profile
    profile = get_bot_profile()
    if not profile:
        print("\n❌ Could not retrieve bot profile.")
        sys.exit(1)
    
    # Test 3: Recent games
    games = get_recent_games(5)
    if not games:
        print("\n⚠️  No recent games found or retrieval failed.")
    
    # Test 4: Streaming capability
    test_game_stream()
    
    # Test 5: Performance stats
    get_performance_stats()
    
    print("\n" + "=" * 60)
    print("✅ API Testing Complete!")
    print("💡 Ready for automated data pipeline integration")
    print("=" * 60)

if __name__ == "__main__":
    main()