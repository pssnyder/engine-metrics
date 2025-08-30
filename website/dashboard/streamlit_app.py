import streamlit as st
import requests
from datetime import datetime
import plotly.express as px
import pandas as pd
import time

# Configuration
BACKEND_URL = "http://localhost:8000"

def test_backend_connection():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

BACKEND_AVAILABLE = test_backend_connection()

# Page configuration
st.set_page_config(
    page_title="Chess Engine Tournament Dashboard",
    page_icon="♕",
    layout="wide"
)

def get_backend_data():
    if not BACKEND_AVAILABLE:
        return None
    try:
        response = requests.get(f"{BACKEND_URL}/api/metrics/comprehensive", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
    return None

def get_backend_status():
    if not BACKEND_AVAILABLE:
        return {'running': False, 'total_games': 0, 'error': 'Backend not available'}
    try:
        response = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'running': True,
                'total_games': data.get('metrics', {}).get('total_games', 0),
                'last_update': data.get('metrics', {}).get('last_updated')
            }
    except Exception as e:
        return {'running': False, 'total_games': 0, 'error': str(e)}
    return {'running': False, 'total_games': 0, 'error': 'Unknown'}

def main():
    st.title("♕ Chess Engine Tournament Dashboard")
    
    # Check backend
    if not BACKEND_AVAILABLE:
        st.error("❌ Backend API not available at http://localhost:8000")
        st.info("Please start the backend with: python backend/app.py")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("Controls")
        auto_refresh = st.checkbox("Auto-refresh (30s)")
        if st.button("🔄 Refresh"):
            st.rerun()
        
        st.header("Status")
        backend_status = get_backend_status()
        if backend_status['running']:
            st.success("✅ Backend: Running")
            st.info(f"📊 Games: {backend_status['total_games']}")
        else:
            st.error("❌ Backend: Stopped")
    
    # Get data
    data = get_backend_data()
    
    if data is None:
        st.warning("⚠️ No data available")
        st.info("Backend may still be processing. Please wait and refresh.")
        return
    
    # Overview
    st.header("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Games", data.get('total_games', 0))
    
    with col2:
        h2h = data.get('head_to_head', {})
        st.metric("Head-to-Head", h2h.get('total_games', 0))
    
    with col3:
        recent = data.get('recent_activity', {})
        recent_count = len(recent.get('recent_games', []))
        st.metric("Recent Games", recent_count)
    
    with col4:
        tournaments = data.get('tournaments', {})
        active = len([t for t in tournaments.get('by_date', {}).values() if t.get('status') == 'active'])
        st.metric("Active Tournaments", active)
    
    # Head-to-head analysis
    st.header("⚔️ Head-to-Head Analysis")
    h2h = data.get('head_to_head', {})
    if h2h:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("V7P3R Wins", h2h.get('v7p3r_wins', 0))
        with col2:
            st.metric("SlowMate Wins", h2h.get('slowmate_wins', 0))
        
        # Pie chart
        v7p3r_wins = h2h.get('v7p3r_wins', 0)
        slowmate_wins = h2h.get('slowmate_wins', 0)
        if v7p3r_wins + slowmate_wins > 0:
            fig = px.pie(
                values=[v7p3r_wins, slowmate_wins],
                names=['V7P3R', 'SlowMate'],
                title="Win Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No head-to-head data available yet")
    
    # Recent activity
    st.header("📈 Recent Activity")
    recent = data.get('recent_activity', {})
    recent_games = recent.get('recent_games', [])
    if recent_games:
        df = pd.DataFrame(recent_games)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent games found")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()
