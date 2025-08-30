"""
Real-time Tournament Dashboard using Streamlit
Displays live tournament data with auto-refresh capabilities.
"""

import streamlit as st
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time

# Add services directory to path
services_path = os.path.join(os.path.dirname(__file__), '..', 'services')
sys.path.insert(0, services_path)

# Add backend directory to path for imports
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

try:
    from realtime_etl import RealTimeETL
    ETL_AVAILABLE = True
except ImportError as e:
    st.error(f"Could not import RealTimeETL: {e}")
    st.info("Please ensure all backend services are properly configured.")
    ETL_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Chess Engine Tournament Dashboard",
    page_icon="♕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}

.tournament-active {
    background-color: #d4edda;
    border-left: 4px solid #28a745;
}

.tournament-recent {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
}

.tournament-completed {
    background-color: #f8d7da;
    border-left: 4px solid #dc3545;
}

.stMetric {
    background-color: white;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'etl' not in st.session_state:
    st.session_state.etl = None
    st.session_state.last_refresh = None
    st.session_state.auto_refresh = True

async def initialize_etl():
    """Initialize the ETL pipeline."""
    if st.session_state.etl is None:
        etl = RealTimeETL()
        if await etl.initialize():
            st.session_state.etl = etl
            return True
    return st.session_state.etl is not None

def format_duration(minutes):
    """Format duration in minutes to human readable format."""
    if minutes < 60:
        return f"{minutes}m"
    else:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

def display_tournament_card(tournament):
    """Display a tournament information card."""
    status = tournament['status']
    status_class = f"tournament-{status}"
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"### {tournament['name']}")
            st.markdown(f"**Status:** {status.title()}")
        
        with col2:
            st.metric("Games", tournament['games_count'])
        
        with col3:
            st.metric("Duration", format_duration(tournament['duration_minutes']))
        
        with col4:
            st.metric("Files", tournament['files_processed'])
        
        # Last update time
        last_update = datetime.fromisoformat(tournament['last_update'])
        time_ago = datetime.now() - last_update
        if time_ago.total_seconds() < 60:
            time_str = "Just now"
        elif time_ago.total_seconds() < 3600:
            time_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
        else:
            time_str = f"{int(time_ago.total_seconds() / 3600)} hours ago"
        
        st.caption(f"Last update: {time_str}")
        st.markdown("---")

def display_head_to_head(head_to_head_data):
    """Display head-to-head statistics."""
    if not head_to_head_data:
        st.info("No head-to-head data available yet")
        return
    
    # V7P3R vs SlowMate stats
    v7p3r_vs_slowmate = head_to_head_data.get('v7p3r_vs_slowmate', {})
    
    if v7p3r_vs_slowmate:
        col1, col2, col3 = st.columns(3)
        
        total_games = v7p3r_vs_slowmate.get('total_games', 0)
        v7p3r_wins = v7p3r_vs_slowmate.get('v7p3r_wins', 0)
        slowmate_wins = v7p3r_vs_slowmate.get('slowmate_wins', 0)
        draws = v7p3r_vs_slowmate.get('draws', 0)
        
        with col1:
            st.metric("V7P3R Wins", v7p3r_wins)
            if total_games > 0:
                win_rate = (v7p3r_wins / total_games) * 100
                st.caption(f"{win_rate:.1f}% win rate")
        
        with col2:
            st.metric("SlowMate Wins", slowmate_wins)
            if total_games > 0:
                win_rate = (slowmate_wins / total_games) * 100
                st.caption(f"{win_rate:.1f}% win rate")
        
        with col3:
            st.metric("Draws", draws)
            if total_games > 0:
                draw_rate = (draws / total_games) * 100
                st.caption(f"{draw_rate:.1f}% draw rate")
        
        # Create pie chart for results
        if total_games > 0:
            fig = px.pie(
                values=[v7p3r_wins, slowmate_wins, draws],
                names=['V7P3R', 'SlowMate', 'Draws'],
                title=f"Head-to-Head Results ({total_games} games)",
                color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c']
            )
            st.plotly_chart(fig, use_container_width=True)

def display_control_engine_stats(control_stats):
    """Display C0BR4 control engine statistics."""
    if not control_stats.get('available', False):
        st.info(control_stats.get('message', 'No control engine data available'))
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Games", control_stats['total_games'])
    
    with col2:
        st.metric("Viability %", f"{control_stats['viability_percentage']:.1f}%")
    
    with col3:
        st.metric("Wins", control_stats['wins'])
    
    with col4:
        st.metric("Draws", control_stats['draws'])
    
    # Viability gauge
    viability_pct = control_stats['viability_percentage']
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = viability_pct,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "C0BR4 Control Engine Viability"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgray"},
                {'range': [25, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

async def main():
    """Main dashboard function."""
    st.title("♕ Chess Engine Tournament Dashboard")
    st.markdown("Real-time monitoring of chess engine tournaments")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Dashboard Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider("Refresh interval (seconds)", 10, 300, 30)
        
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        # ETL status
        st.header("System Status")
        
        # Initialize ETL if needed
        if await initialize_etl():
            etl_status = st.session_state.etl.get_status()
            
            st.success("✅ ETL Pipeline: Running" if etl_status['running'] else "⚠️ ETL Pipeline: Stopped")
            st.info(f"📊 Tournaments Tracked: {etl_status['tournaments_tracked']}")
            
            if etl_status['last_update']:
                last_update = datetime.fromisoformat(etl_status['last_update'])
                st.info(f"🕒 Last Update: {last_update.strftime('%H:%M:%S')}")
        else:
            st.error("❌ ETL Pipeline: Failed to initialize")
            st.stop()
    
    # Main dashboard content
    if st.session_state.etl:
        try:
            # Get real-time stats
            stats = await st.session_state.etl.get_realtime_stats()
            
            if 'error' in stats:
                st.error(f"Error loading stats: {stats['error']}")
                return
            
            # Overview metrics
            st.header("📊 Live Overview")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Active Tournaments", stats['active_tournaments'])
            
            with col2:
                st.metric("Total Tournaments", stats['tournament_count'])
            
            with col3:
                st.metric("Games Today", stats['total_games_today'])
            
            with col4:
                last_update_str = "Never" if not stats['last_update'] else datetime.fromisoformat(stats['last_update']).strftime('%H:%M:%S')
                st.metric("Last Update", last_update_str)
            
            # Live tournaments
            st.header("🏆 Live Tournaments")
            live_tournaments = stats['live_tournaments']
            
            if live_tournaments:
                for tournament in live_tournaments:
                    display_tournament_card(tournament)
            else:
                st.info("No active tournaments at the moment")
            
            # Head-to-head statistics
            st.header("⚔️ Head-to-Head: V7P3R vs SlowMate")
            display_head_to_head(stats['head_to_head'])
            
            # Control engine statistics
            st.header("🎯 Control Engine Performance")
            display_control_engine_stats(stats['control_engine_stats'])
            
            # Recent activity
            st.header("📈 Recent Activity")
            recent_activity = stats['recent_activity']
            
            if recent_activity:
                for activity in recent_activity:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"**{activity['tournament']}**")
                        
                        with col2:
                            st.write(f"Games: {activity['games_added']}")
                        
                        with col3:
                            timestamp = datetime.fromisoformat(activity['timestamp'])
                            st.write(timestamp.strftime('%H:%M:%S'))
                        
                        st.markdown("---")
            else:
                st.info("No recent activity")
                
        except Exception as e:
            st.error(f"Error loading dashboard data: {e}")
    
    # Auto-refresh
    if st.session_state.auto_refresh and auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
