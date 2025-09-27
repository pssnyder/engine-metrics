# Move Layer - Chess Engine Metrics Pipeline

## Overview

The Move Layer is the first stage of our cloud-native big data pipeline for chess engine metrics. It automatically monitors the local `raw_data` directory and synchronizes any new or modified files with a Google Cloud Storage bucket, enabling seamless data flow from local development to cloud processing.

## Architecture

```
Local raw_data/ → Move Layer → Cloud Storage Bucket → Ingest Pipeline
```

The Move Layer acts as a bridge between local file storage and cloud infrastructure, handling:

- **Real-time file monitoring** using filesystem watchers
- **Initial synchronization** of existing files
- **Incremental uploads** for new and modified files
- **File state tracking** to avoid redundant uploads
- **Error handling and retry logic** for robust operation
- **Comprehensive logging** for monitoring and debugging

## Key Components

### 1. CloudStorageUploader
Handles all Google Cloud Storage interactions:
- File uploads with metadata
- Bucket validation
- Authentication management
- Upload progress tracking

### 2. FileTracker
Maintains local state of file synchronization:
- Tracks file hashes to detect changes
- Persists state across service restarts
- Identifies new files for upload

### 3. RawDataFileHandler
Implements the Watchdog file system event handler:
- Monitors create, modify, and move events
- Filters relevant file types
- Triggers upload operations

### 4. MoveLayer
Main service orchestrator:
- Coordinates all components
- Manages service lifecycle
- Handles graceful shutdown

## Configuration

The Move Layer uses `move_layer_config.json` for configuration:

```json
{
  "move_layer_config": {
    "local_paths": {
      "raw_data_directory": "path/to/raw_data",
      "state_file": "file_tracker_state.json",
      "log_file": "move_layer.log"
    },
    "cloud_storage": {
      "bucket_name": "your-bucket-name",
      "project_id": "your-project-id",
      "credentials_path": null
    },
    "monitoring": {
      "file_patterns": ["*.pgn", "*.json", "*.csv"],
      "exclude_patterns": [".*", "*.tmp"],
      "upload_delay_seconds": 2
    }
  }
}
```

## Setup and Installation

### 1. Install Dependencies
```bash
pip install -r requirements_move_layer.txt
```

### 2. Configure Google Cloud
```bash
# Install Google Cloud SDK
# Authenticate with your Google Cloud account
gcloud auth application-default login

# Set your project
gcloud config set project your-project-id
```

### 3. Update Configuration
Edit `move_layer_config.json`:
- Set `bucket_name` to your Cloud Storage bucket
- Set `project_id` to your Google Cloud project
- Adjust file patterns and paths as needed

### 4. Run Setup
```bash
python setup_move_layer.py
```

### 5. Start the Service
```bash
python run_move_layer.py
```

## File Types Supported

The Move Layer monitors and uploads:
- **PGN files** (`.pgn`) - Chess game notation
- **JSON files** (`.json`) - Structured data
- **CSV files** (`.csv`) - Tabular data
- **Markdown files** (`.md`) - Documentation
- **Text files** (`.txt`) - General text data
- **Log files** (`.log`) - Application logs

## Monitoring and Logging

### Log Levels
- **INFO**: Normal operation events (file uploads, sync status)
- **WARNING**: Recoverable issues (retry attempts, missing files)
- **ERROR**: Serious problems (upload failures, configuration errors)

### Log File Locations
- Service logs: `logs/move_layer.log`
- State file: `state/file_tracker_state.json`

### Monitoring Metrics
The service tracks:
- Files uploaded successfully
- Upload failures and retries
- Processing time per file
- Total data transferred

## Error Handling

### Retry Logic
- Failed uploads are retried up to 3 times
- Exponential backoff between retry attempts
- Permanent failures are logged for manual review

### State Recovery
- Service state is persisted to disk
- Graceful recovery after service restarts
- Incomplete uploads are automatically resumed

### Common Issues

**Authentication Errors**
```
Solution: Ensure Google Cloud credentials are properly configured
Command: gcloud auth application-default login
```

**Bucket Access Denied**
```
Solution: Verify bucket permissions and project settings
Check: IAM roles include Storage Admin or Storage Object Admin
```

**File System Permissions**
```
Solution: Ensure the service has read access to raw_data directory
Check: Directory permissions and user access rights
```

## Integration with Pipeline

The Move Layer is the first stage of the four-stage pipeline:

1. **Move** (This service): Local → Cloud Storage
2. **Ingest**: Cloud Storage → Data Lake (BigQuery)
3. **Transform**: Data Lake → Conformed Dataset
4. **Report**: Conformed Dataset → Analytics/Visualization

## Performance Considerations

### Batch Processing
- Files are uploaded individually for real-time processing
- Consider batching for high-volume scenarios
- Current design optimized for tournament data volumes

### Network Efficiency
- Only modified files are uploaded (hash-based detection)
- Compression can be enabled in configuration
- Parallel uploads for multiple files

### Resource Usage
- Minimal CPU overhead from file watching
- Memory usage scales with number of files tracked
- Disk usage for state and log files is minimal

## Development and Testing

### Local Testing
1. Create test files in `raw_data/test/`
2. Start the Move Layer service
3. Observe uploads in Cloud Storage console
4. Check logs for successful operations

### Unit Tests
```bash
python -m pytest tests/test_move_layer.py
```

### Integration Tests
```bash
python tests/integration/test_cloud_upload.py
```

## Future Enhancements

### Planned Features
- **Real-time notifications** (Slack, email alerts)
- **Bandwidth throttling** for network optimization
- **File compression** before upload
- **Metadata enrichment** with chess engine context
- **Multi-bucket support** for different data types

### Scalability Improvements
- **Multiple worker threads** for parallel processing
- **Queue-based architecture** for high-volume scenarios
- **Kubernetes deployment** for cloud-native operation
- **Monitoring dashboards** with Grafana/Prometheus

## Troubleshooting

### Debug Mode
Enable detailed logging by setting log level to DEBUG in configuration.

### Service Status Check
```bash
# Check if service is running
ps aux | grep move_layer

# View recent logs
tail -f logs/move_layer.log
```

### Manual File Upload
For testing or manual operations:
```bash
python -c "from move_layer import CloudStorageUploader; uploader = CloudStorageUploader(config); uploader.upload_file('path/to/file')"
```

## Support

For issues or questions:
1. Check the logs in `logs/move_layer.log`
2. Verify configuration in `move_layer_config.json`
3. Test Google Cloud connectivity
4. Review this documentation for common solutions

---

*The Move Layer is a critical component of the chess engine metrics platform, ensuring reliable data flow from local development to cloud-based analytics and AI processing.*