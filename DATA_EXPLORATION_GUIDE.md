# Chess Engine Data Exploration Guide

## Overview
You have rich datasets across two main areas:
1. **Tournament Game Records** (PGN files) - Raw game data from engine battles
2. **Engine Analysis Results** (JSON files) - Tactical, positional, and performance analysis

## Quick Start: Data Inventory

### 1. Tournament Data (game_records/)
```bash
# Count total games across all tournaments
find "game_records" -name "*.pgn" -exec wc -l {} \; | awk '{sum+=$1} END {print "Approximate games:", sum/50}'

# List tournaments by date
ls -la game_records/ | grep "Engine Battle"

# Check file sizes to find biggest tournaments
find "game_records" -name "*.pgn" -exec ls -lh {} \; | sort -k5 -hr
```

### 2. Analysis Data (engine-tester/)
```bash
# Find all JSON analysis files
find "engine-tester" -name "*.json" -type f

# Check analysis file sizes and types
find "engine-tester" -name "*analysis*.json" -exec ls -lh {} \;
find "engine-tester" -name "*comparison*.json" -exec ls -lh {} \;
find "engine-tester" -name "*test*.json" -exec ls -lh {} \;
```

## Data Exploration Tools & Workflows

### A. Python + Pandas for Data Processing

#### Setup Environment
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import chess.pgn
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Set up plotting
plt.style.use('dark_background')
sns.set_theme(style="darkgrid")
```

#### PGN Data Processing
```python
def parse_pgn_file(pgn_path):
    """Extract game metadata and results from PGN file."""
    games = []
    with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            
            games.append({
                'white': game.headers.get('White', ''),
                'black': game.headers.get('Black', ''),
                'result': game.headers.get('Result', ''),
                'date': game.headers.get('Date', ''),
                'event': game.headers.get('Event', ''),
                'plycount': int(game.headers.get('PlyCount', 0)) if game.headers.get('PlyCount', '').isdigit() else 0,
                'time_control': game.headers.get('TimeControl', ''),
                'termination': game.headers.get('Termination', ''),
                'round': game.headers.get('Round', ''),
                'eco': game.headers.get('ECO', ''),
                'opening': game.headers.get('Opening', '')
            })
    return pd.DataFrame(games)

# Example usage
df = parse_pgn_file("game_records/Engine Battle 20250830/Engine Battle 20250830.pgn")
print(df.head())
print(f"Total games: {len(df)}")
print(f"Unique engines: {set(df['white'].tolist() + df['black'].tolist())}")
```

#### JSON Analysis Processing
```python
def load_analysis_file(json_path):
    """Load and explore JSON analysis files."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

# Example: Load tactical analysis
tactical_data = load_analysis_file("engine-tester/v7p3r_puzzle_analysis_20250829_113929.json")
print("Keys in tactical analysis:", tactical_data.keys())

# Convert to DataFrame for exploration
if 'puzzles' in tactical_data:
    puzzle_df = pd.DataFrame(tactical_data['puzzles'])
    print(puzzle_df.columns)
```

### B. VS Code Extensions for Data Exploration

#### Recommended Extensions:
1. **Data Wrangler** - Visual data exploration and cleaning
2. **Jupyter** - Interactive notebooks in VS Code
3. **Python** - IntelliSense and debugging
4. **Rainbow CSV** - Better CSV viewing
5. **Excel Viewer** - View CSV/Excel files visually

#### VS Code Data Workflows:
```python
# Create exploration notebook: analysis_notebook.ipynb
# Use Command Palette: "Jupyter: Create New Blank Notebook"

# In notebook cells:
# Cell 1: Data loading
df = parse_pgn_file("path/to/pgn")

# Cell 2: Quick stats
df.describe()
df['result'].value_counts()

# Cell 3: Visualizations
df['white'].value_counts().plot(kind='bar')
plt.show()
```

### C. Specific Data Exploration Ideas

#### 1. Engine Performance Analysis
```python
def analyze_engine_performance(df):
    """Analyze engine win rates, openings, time usage."""
    
    # Win rates by engine
    results = []
    for engine in df['white'].unique():
        white_games = df[df['white'] == engine]
        black_games = df[df['black'] == engine]
        
        white_wins = len(white_games[white_games['result'] == '1-0'])
        black_wins = len(black_games[black_games['result'] == '0-1'])
        total_games = len(white_games) + len(black_games)
        
        results.append({
            'engine': engine,
            'total_games': total_games,
            'wins': white_wins + black_wins,
            'win_rate': (white_wins + black_wins) / total_games if total_games > 0 else 0
        })
    
    return pd.DataFrame(results)

# Usage
performance = analyze_engine_performance(df)
performance.sort_values('win_rate', ascending=False)
```

#### 2. Opening Analysis
```python
def analyze_openings(df):
    """Analyze opening frequencies and success rates."""
    
    # Opening frequency
    opening_freq = df['opening'].value_counts()
    
    # Opening success by engine
    opening_results = df.groupby(['opening', 'white']).agg({
        'result': ['count', lambda x: (x == '1-0').sum()]
    }).round(3)
    
    return opening_freq, opening_results

openings, opening_success = analyze_openings(df)
print("Most common openings:")
print(openings.head(10))
```

#### 3. Time Analysis
```python
def analyze_game_lengths(df):
    """Analyze game lengths and patterns."""
    
    # Game length distribution
    df['game_length'] = df['plycount'] / 2  # Convert to moves
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Histogram of game lengths
    axes[0,0].hist(df['game_length'], bins=30, alpha=0.7)
    axes[0,0].set_title('Game Length Distribution')
    axes[0,0].set_xlabel('Moves')
    
    # Box plot by result
    df.boxplot(column='game_length', by='result', ax=axes[0,1])
    axes[0,1].set_title('Game Length by Result')
    
    # Engine comparison
    v7p3r_games = df[(df['white'].str.contains('v7p3r', case=False)) | 
                     (df['black'].str.contains('v7p3r', case=False))]
    slowmate_games = df[(df['white'].str.contains('slowmate', case=False)) | 
                        (df['black'].str.contains('slowmate', case=False))]
    
    axes[1,0].hist([v7p3r_games['game_length'], slowmate_games['game_length']], 
                   label=['V7P3R', 'SlowMate'], alpha=0.7)
    axes[1,0].set_title('Game Length by Engine')
    axes[1,0].legend()
    
    plt.tight_layout()
    plt.show()

analyze_game_lengths(df)
```

### D. Interactive Exploration Tools

#### 1. Plotly Dashboards
```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_interactive_dashboard(df):
    """Create interactive plots for data exploration."""
    
    # Win rate comparison
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Win Rates', 'Game Lengths', 'Results Over Time', 'Opening Distribution'),
        specs=[[{"type": "bar"}, {"type": "histogram"}],
               [{"type": "scatter"}, {"type": "pie"}]]
    )
    
    # Add traces...
    performance = analyze_engine_performance(df)
    
    fig.add_trace(
        go.Bar(x=performance['engine'], y=performance['win_rate'], name='Win Rate'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Histogram(x=df['plycount']/2, name='Game Length'),
        row=1, col=2
    )
    
    fig.show()

create_interactive_dashboard(df)
```

#### 2. Streamlit Quick Explorer
```python
# Create: quick_explorer.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Chess Engine Data Explorer")

# File upload
uploaded_file = st.file_uploader("Choose a PGN file", type="pgn")

if uploaded_file:
    df = parse_pgn_file(uploaded_file)
    
    st.write(f"Total games: {len(df)}")
    
    # Engine selection
    engines = st.multiselect("Select engines to analyze", df['white'].unique())
    
    if engines:
        filtered_df = df[(df['white'].isin(engines)) | (df['black'].isin(engines))]
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(filtered_df, x='result', title='Results Distribution')
            st.plotly_chart(fig)
        
        with col2:
            fig = px.box(filtered_df, y='plycount', title='Game Lengths')
            st.plotly_chart(fig)

# Run with: streamlit run quick_explorer.py
```

### E. Specific Analysis Questions to Explore

#### Head-to-Head Analysis
```python
def head_to_head_analysis(df, engine1, engine2):
    """Detailed head-to-head comparison."""
    
    h2h = df[
        ((df['white'].str.contains(engine1, case=False)) & (df['black'].str.contains(engine2, case=False))) |
        ((df['white'].str.contains(engine2, case=False)) & (df['black'].str.contains(engine1, case=False)))
    ]
    
    print(f"Head-to-head games: {len(h2h)}")
    print(f"Results distribution:")
    print(h2h['result'].value_counts())
    
    # Win rates by color
    engine1_white = h2h[h2h['white'].str.contains(engine1, case=False)]
    engine1_black = h2h[h2h['black'].str.contains(engine1, case=False)]
    
    print(f"\n{engine1} as White: {len(engine1_white)} games")
    print(engine1_white['result'].value_counts())
    print(f"\n{engine1} as Black: {len(engine1_black)} games")
    print(engine1_black['result'].value_counts())

# Usage
head_to_head_analysis(df, 'v7p3r', 'slowmate')
```

## Recommended Exploration Workflow

### Phase 1: Data Inventory (30 minutes)
1. Run file counts and size analysis
2. Load 2-3 PGN files to understand structure
3. Examine 2-3 JSON files to understand analysis format

### Phase 2: Basic Analysis (1-2 hours)
1. Create engine performance summaries
2. Analyze opening frequencies
3. Look at game length patterns
4. Basic head-to-head statistics

### Phase 3: Deep Dive (ongoing)
1. Correlate JSON analysis with PGN results
2. Time-series analysis of engine improvement
3. Position-specific analysis
4. Opening preparation analysis

### Phase 4: Visualization (1-2 hours)
1. Create summary dashboards
2. Interactive exploration tools
3. Export key findings

Would you like me to help you start with any specific analysis, or would you prefer to begin with a particular dataset (PGN games vs JSON analysis files)?
