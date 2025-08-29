# Engine Metrics Dashboard

A comprehensive web-based dashboard for monitoring chess engine performance, specifically designed to track the battle between V7P3R (manual development) and SlowMate (AI-driven development).

## Features

- **Real-time Monitoring**: Automatic detection and processing of new PGN files
- **Head-to-Head Metrics**: Detailed performance comparison between target engines
- **Custom Classifications**: 
  - Decisive wins (checkmates and resignations by material advantage)
  - Soft losses (losses by adjudication/time/other non-mate factors)
  - Missed wins (draws/losses with material advantage)
- **Batch Processing**: Handles encoding issues and processes files every 5 minutes
- **Network Support**: Monitor multiple PCs via network shares or synced directories
- **Web Interface**: Clean, responsive dashboard accessible from any device on your network

## Quick Start

### Windows Setup

1. **Clone/Download** this repository to your main PC
2. **Run Setup**: Double-click `setup.bat` to install dependencies
3. **Configure**: Edit `config/settings.yaml` to add your PGN directories
4. **Start Dashboard**: Run `start-backend.bat` for basic usage

### Configuration

Edit `config/settings.yaml` to customize:

```yaml
# Add your PGN directories
directories:
  local_paths:
    - "./data/game_records"        # Existing directory
    - "C:/Arena/Tournaments"       # Add your Arena output directory
  
  network_paths:
    - "//PC2/ChessResults"         # Network share from another PC
    - "./synced_data/pc3_results"  # Or synced local directory

# Customize processing
processing:
  batch_interval_minutes: 5        # How often to check for new files

# Engine settings  
engines:
  target_engines:
    - v7p3r                        # Your engine names (case insensitive)
    - slowmate
```

## Usage Modes

### 1. Backend Only (`start-backend.bat`)
- Runs the web server on port 8000
- Serves the dashboard at `http://localhost:8000`
- Best for production use

### 2. Development Mode (`start-development.bat`)
- Runs backend + frontend development server
- Live reload for code changes
- Access at `http://localhost:3000` (development) or `http://localhost:8000` (production)

### 3. Production Mode (`start-production.bat`)
- Builds optimized frontend and serves from backend
- Single server deployment

## Dashboard Features

### Main Dashboard
- **Engine Statistics**: Win/loss rates, decisive wins, soft losses, missed wins
- **Head-to-Head Breakdown**: Direct comparison metrics
- **System Status**: Processing status and health monitoring
- **Real-time Updates**: Automatic refresh every 5 minutes

### Game History
- **Search & Filter**: Find games by player, result, termination type
- **Classification Tags**: Visual indicators for game types
- **Detailed Stats**: Time per move, search depth, material tracking

### Settings
- **System Configuration**: View current settings and monitored directories
- **Directory Status**: Check which directories are accessible
- **Processing Info**: Monitor batch processing status

## Architecture

```
engine-metrics/
├── backend/           # Python FastAPI server
│   ├── main.py       # Application entry point
│   ├── api/          # REST API endpoints
│   ├── services/     # Business logic
│   │   ├── pgn_processor.py     # PGN file processing
│   │   ├── metrics_calculator.py # Metrics computation
│   │   └── file_watcher.py      # Directory monitoring
│   └── database/     # SQLite database models
├── frontend/         # React web interface
├── config/           # Configuration files
├── data/            # Default PGN storage
└── database/        # SQLite database files
```

## Technical Details

### PGN Processing
- **Encoding Handling**: Automatically detects and handles UTF-8 errors
- **Duplicate Prevention**: Files are hashed to prevent reprocessing
- **Engine Filtering**: Only processes games between versioned target engines
- **Move Analysis**: Extracts time, depth, and material advantage data

### Metrics Calculation
- **Material Tracking**: Monitors material advantage throughout games
- **Custom Classifications**: Applies sophisticated game outcome analysis
- **Performance Caching**: Metrics cached for 1 hour to improve performance
- **Head-to-Head Focus**: All statistics focus on target engine matchups only

### Network Monitoring
- **Multiple Sources**: Monitor Arena output on multiple PCs
- **Flexible Paths**: Supports Windows shares, mapped drives, or synced folders
- **Automatic Detection**: New files processed within 5 minutes

## Troubleshooting

### Common Issues

1. **"No games found"**
   - Check that PGN files contain versioned engine names (e.g., "v7p3r_v1.2", "slowmate_v2.1")
   - Verify directory paths in `config/settings.yaml`
   - Check the Settings page for directory status

2. **"Directory not found"**
   - Ensure paths use forward slashes or escaped backslashes
   - For network paths, verify the remote PC is accessible
   - Check Windows firewall/sharing settings

3. **"Encoding errors"**
   - The system automatically handles common encoding issues
   - Files with errors are processed with replacement characters
   - Check processing logs in the database

4. **"No updates"**
   - Verify file watcher is running (check Settings page)
   - Ensure PGN files are at least 30 seconds old (prevents processing incomplete files)
   - Check that games are between the configured target engines

### Performance Tips

- **Large Datasets**: The system handles thousands of games efficiently
- **Network Latency**: Local syncing may be faster than network shares
- **Database Growth**: SQLite database will grow over time but remains fast
- **Memory Usage**: Backend uses minimal resources, suitable for always-on operation

## Development

### Adding Features
- **Backend**: Add new API endpoints in `backend/api/`
- **Frontend**: Add new React components in `frontend/src/components/`
- **Metrics**: Extend `MetricsCalculator` for new statistical analysis

### Database Schema
- **Games**: Individual game records with detailed analysis
- **ProcessingLog**: File processing history and error tracking
- **MetricsCache**: Computed metrics cache for performance

## Support

For issues specific to your chess engine development:
1. Check the Settings page for system status
2. Review PGN file formats and engine naming
3. Monitor the processing logs for errors
4. Verify network connectivity for multi-PC setups

This dashboard is designed to run continuously, automatically processing new tournament results as your engines battle for supremacy!
