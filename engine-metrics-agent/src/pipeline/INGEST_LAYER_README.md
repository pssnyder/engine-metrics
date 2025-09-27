# Ingest Layer - Chess Engine Metrics Pipeline

## Overview

The Ingest Layer is the second stage of our cloud-native big data pipeline. It monitors the Cloud Storage bucket for new files and automatically ingests them into BigQuery (our data lake), transforming raw files into structured, queryable datasets optimized for AI processing and analytics.

## Architecture

```
Cloud Storage Bucket → Ingest Layer → BigQuery Data Lake → Transform Layer
```

The Ingest Layer handles:

- **File monitoring** - Scans storage bucket for new files
- **Multi-format processing** - Handles PGN, JSON, Markdown, and text files
- **Schema validation** - Ensures data conforms to BigQuery schemas
- **Batch and streaming ingestion** - Supports both modes
- **Error handling** - Robust retry logic and failure tracking
- **Data quality** - Validation and deduplication

## Key Components

### 1. SchemaManager
Defines BigQuery table schemas for different data types:
- **PGN Games**: Chess game records with metadata
- **Analysis Results**: Engine analysis data and metrics
- **Documentation**: Development docs and notes

### 2. DataProcessor
Transforms raw files into structured records:
- **PGN Parser**: Extracts game metadata and moves
- **JSON Parser**: Processes analysis results and metrics
- **Markdown Parser**: Structures documentation content

### 3. BigQueryManager
Manages all BigQuery operations:
- Dataset and table creation
- Schema enforcement
- Batch data insertion
- Error handling and retries

### 4. CloudStorageMonitor
Monitors storage bucket for changes:
- File discovery and tracking
- Parallel processing
- Progress tracking and resumption

## Data Lake Schema

### Games Table (`pgn_games`)
Stores chess game records from PGN files:

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | STRING | Unique game identifier |
| `event` | STRING | Tournament/event name |
| `white` | STRING | White player name |
| `black` | STRING | Black player name |
| `result` | STRING | Game result (1-0, 0-1, 1/2-1/2) |
| `moves` | STRING | Complete game moves |
| `move_count` | INTEGER | Number of moves played |
| `source_file` | STRING | Original PGN filename |
| `ingested_at` | TIMESTAMP | Ingestion timestamp |

### Analysis Table (`analysis_results`)
Stores engine analysis data from JSON files:

| Field | Type | Description |
|-------|------|-------------|
| `analysis_id` | STRING | Unique analysis identifier |
| `engine_version` | STRING | V7P3R version used |
| `analysis_type` | STRING | Type of analysis performed |
| `position_fen` | STRING | Position analyzed (FEN) |
| `evaluation` | FLOAT | Position evaluation |
| `best_move` | STRING | Engine's best move |
| `depth` | INTEGER | Search depth |
| `nodes_searched` | INTEGER | Nodes evaluated |
| `analysis_data` | JSON | Complete analysis data |
| `ingested_at` | TIMESTAMP | Ingestion timestamp |

### Documentation Table (`documentation`)
Stores development documentation from Markdown files:

| Field | Type | Description |
|-------|------|-------------|
| `doc_id` | STRING | Unique document identifier |
| `title` | STRING | Document title |
| `content` | STRING | Full document content |
| `engine_version` | STRING | Related engine version |
| `doc_type` | STRING | Document category |
| `source_file` | STRING | Original filename |
| `ingested_at` | TIMESTAMP | Ingestion timestamp |

## Configuration

The Ingest Layer uses `ingest_layer_config.json`:

```json
{
  "ingest_layer_config": {
    "storage": {
      "bucket_name": "your-bucket-name"
    },
    "bigquery": {
      "project_id": "your-project-id",
      "dataset_name": "chess_engine_data_lake"
    },
    "processing": {
      "max_workers": 4,
      "batch_size": 100
    },
    "monitoring": {
      "polling_interval": 60
    }
  }
}
```

## Setup and Installation

### 1. Install Dependencies
```bash
pip install -r requirements_ingest_layer.txt
```

### 2. Configure BigQuery
Ensure your Google Cloud project has BigQuery API enabled:
```bash
gcloud services enable bigquery.googleapis.com
```

### 3. Update Configuration
Edit `ingest_layer_config.json` with your project details.

### 4. Run Setup
```bash
python setup_ingest_layer.py
```

### 5. Start Ingestion
```bash
python run_ingest_layer.py
```

## Operation Modes

### Initial Batch Ingestion
Processes all existing files in the bucket:
- Scans entire bucket for files
- Processes files in parallel
- Tracks progress and failures
- Resumes from interruptions

### Continuous Monitoring
Watches for new files and processes them automatically:
- Polls bucket at configured intervals
- Processes new files immediately
- Maintains state across restarts
- Logs all activities

### Hybrid Mode
Combines both approaches:
1. Initial batch processing of existing files
2. Continuous monitoring for new files

## Data Processing Logic

### PGN File Processing
1. **Parse headers** - Extract game metadata (Event, Site, Date, Players, etc.)
2. **Parse moves** - Extract and validate move sequences
3. **Generate identifiers** - Create unique game IDs
4. **Enrich data** - Add derived fields (move count, duration)
5. **Insert records** - Store in BigQuery games table

### Analysis File Processing
1. **Parse JSON** - Handle various analysis result formats
2. **Extract metrics** - Evaluation, depth, time, nodes
3. **Normalize data** - Standardize field names and types
4. **Preserve raw data** - Keep original JSON in analysis_data field
5. **Insert records** - Store in BigQuery analysis table

### Documentation Processing
1. **Extract metadata** - Title, engine version, type
2. **Parse content** - Handle markdown formatting
3. **Extract tags** - Identify key topics (future enhancement)
4. **Generate identifiers** - Create unique doc IDs
5. **Insert records** - Store in BigQuery documentation table

## Monitoring and Logging

### Logging Levels
- **INFO**: Normal processing events (files ingested, records inserted)
- **WARNING**: Non-critical issues (unsupported files, validation warnings)
- **ERROR**: Processing failures (parse errors, BigQuery issues)

### Metrics Tracked
- Files processed per hour
- Records inserted per table
- Processing success rate
- Error rates by file type
- Average processing time

### Status Monitoring
```python
# Get current status
status = ingest_layer.get_status()
print(status)
# {
#   'bucket': 'your-bucket-name',
#   'dataset': 'chess_engine_data_lake', 
#   'processed_files_count': 125,
#   'last_check': '2025-09-26T10:30:00Z'
# }
```

## Error Handling

### Retry Logic
- Failed processing attempts are retried up to 3 times
- Exponential backoff between retries
- Permanent failures are logged for manual review

### Data Quality
- Schema validation before insertion
- Duplicate detection and handling
- Invalid record rejection or correction
- Data quality metrics tracking

### Recovery
- Service state is persisted to disk
- Graceful recovery after interruptions
- Resumption from last successful checkpoint

## Performance Optimization

### Parallel Processing
- Multiple worker threads for file processing
- Configurable concurrency levels
- Balanced load across CPU cores

### Batch Operations
- Efficient BigQuery batch insertions
- Optimized memory usage
- Streaming for large files

### BigQuery Optimization
- Partitioned tables by date
- Clustered tables by key fields
- Optimized for analytical queries

## Integration with Pipeline Stages

### Input: Move Layer
Receives files uploaded by the Move Layer from local storage.

### Output: Transform Layer
Provides structured data in BigQuery for the Transform Layer to create conformed datasets.

### Data Flow
```
Move Layer → Cloud Storage → Ingest Layer → BigQuery → Transform Layer
```

## Troubleshooting

### Common Issues

**BigQuery Permission Errors**
```
Solution: Ensure service account has BigQuery Data Editor role
Check: IAM permissions for BigQuery dataset
```

**Schema Mismatch Errors**
```
Solution: Verify table schemas match expected data format
Check: Review sample data in failed files
```

**Storage Access Denied**
```
Solution: Verify bucket permissions and project settings
Check: Service account has Storage Object Viewer role
```

### Debug Mode
Enable detailed logging by setting log level to DEBUG in configuration.

### Manual Processing
For testing or recovery:
```python
from ingest_layer import IngestLayer
ingest_layer = IngestLayer()
stats = ingest_layer.run_initial_ingestion()
```

## Future Enhancements

### Planned Features
- **Real-time processing** with Pub/Sub triggers
- **Data validation** with Great Expectations
- **Schema evolution** and migration tools
- **Advanced parsing** for more file formats
- **ML-based content analysis** for documentation

### Scalability Improvements
- **Apache Beam** for distributed processing
- **Dataflow** for managed pipeline execution
- **Cloud Functions** for event-driven processing
- **Monitoring dashboards** with Grafana

---

*The Ingest Layer is a critical component that transforms raw chess engine data into a structured, queryable data lake, enabling advanced analytics and AI processing in subsequent pipeline stages.*