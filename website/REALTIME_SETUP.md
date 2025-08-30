# Real-time Tournament Monitoring Setup

## Overview

This system provides real-time monitoring of chess engine tournaments with automatic file processing and live dashboard updates.

## Components

1. **Arena Monitor Service** - Watches Arena tournaments directory for new files
2. **Real-time ETL Pipeline** - Processes tournament data as it arrives
3. **Streamlit Dashboard** - Live visualization with auto-refresh
4. **Tournament Monitor Service** - Coordinates all components

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements_realtime.txt
```

### 2. Configure Settings

Edit `config/settings.yaml` to match your setup:

```yaml
arena_monitor:
  arena_tournaments_dir: "C:\\Program Files (x86)\\Arena\\Tournaments"
  target_dir: "S:\\Maker Stuff\\Programming\\Chess Engines\\Chess Engine Playground\\engine-metrics\\game_records"
```

### 3. Start the System

#### Option A: Start Everything at Once

Run both services:
1. Double-click `start_monitor.bat` (starts file monitoring)
2. Double-click `start_dashboard.bat` (starts Streamlit dashboard)

#### Option B: Manual Start

```bash
# Terminal 1 - Start monitoring service
cd services
python tournament_monitor.py

# Terminal 2 - Start dashboard
cd dashboard
streamlit run streamlit_app.py
```

## Features

### Real-time File Monitoring
- Automatically detects new tournament files in Arena directory
- Organizes files by date and tournament type
- Handles file conflicts and duplicates

### Live Dashboard Features
- **Tournament Overview**: Active tournaments, total games, live status
- **Head-to-Head Stats**: V7P3R vs SlowMate detailed statistics
- **Control Engine Monitoring**: C0BR4 viability and performance metrics
- **Live Activity Feed**: Recent tournament updates and file processing
- **Auto-refresh**: Configurable refresh intervals (10-300 seconds)

### Tournament Organization
Files are automatically organized into directories like:
```
game_records/
├── Engine Battle 20250824/
│   ├── Engine Battle 20250824.pgn
│   ├── Engine Battle 20250824.log
│   └── Engine Battle 20250824.txt
└── SlowMate Tournament 20250824/
    ├── SlowMate Tournament 20250824.pgn
    └── SlowMate Tournament 20250824.res
```

## Dashboard Access

Once started, the dashboard is available at:
- **Local**: http://localhost:8501
- **Network**: http://[your-pc-ip]:8501

## System Requirements

- Python 3.8+
- Windows 10/11 (for Arena integration)
- 4GB RAM recommended
- Network access for multi-PC viewing

## Troubleshooting

### Arena Directory Not Found
Check that Arena is installed and the path in settings.yaml is correct:
```yaml
arena_tournaments_dir: "C:\\Program Files (x86)\\Arena\\Tournaments"
```

### Permission Errors
Run as Administrator if accessing system directories.

### Dashboard Not Loading
1. Check if Streamlit is running: `streamlit --version`
2. Verify no other service is using port 8501
3. Check firewall settings for network access

### Files Not Processing
1. Verify Arena monitor is running
2. Check log file: `tournament_monitor.log`
3. Ensure target directory is accessible

## Configuration Options

### Dashboard Settings
```yaml
dashboard:
  auto_refresh_seconds: 30      # Default refresh interval
  max_concurrent_tournaments: 10 # Maximum tournaments to track
  show_live_games: true         # Show individual game updates
```

### Processing Settings
```yaml
processing:
  batch_interval_minutes: 1     # ETL processing frequency
  encoding_fallbacks: ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
```

### File Monitoring
```yaml
arena_monitor:
  file_extensions: [".pgn", ".txt", ".log", ".html", ".res", ".at"]
  auto_process: true
  process_delay_seconds: 5      # Wait time after file creation
```

## Performance Tips

1. **Reduce Refresh Rate**: Set higher refresh intervals for better performance
2. **Limit Tournament History**: System automatically focuses on last 24 hours
3. **Network Access**: Use local IP address for faster loading on other devices
4. **File Processing**: Larger PGN files may take longer to process

## Advanced Usage

### Custom Tournament Detection
Add patterns to detect different tournament types:
```yaml
tournament_patterns:
  my_tournament: "My Custom Tournament"
  special_event: "Special Event"
```

### Multiple Arena Instances
Monitor multiple Arena installations:
```yaml
arena_monitor:
  directories:
    - "C:\\Program Files (x86)\\Arena\\Tournaments"
    - "D:\\Arena2\\Tournaments"
```

### API Integration
The system can be extended to provide REST API endpoints for external integration.

## Logs and Monitoring

- **Monitor Log**: `tournament_monitor.log`
- **Streamlit Log**: Console output from dashboard
- **ETL Processing**: Logged to main application log

## Next Steps

1. Set up automatic startup with Windows Task Scheduler
2. Configure network firewall rules for remote access
3. Consider running as Windows Service for production use
4. Add custom tournament types and engine configurations

## Support

Check the logs for detailed error information. Common issues are usually related to:
- File permissions
- Network paths
- Python environment setup
- Arena installation paths
