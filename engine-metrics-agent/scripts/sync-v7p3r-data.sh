#!/bin/bash

# V7P3R Data Sync Script
# Syncs local V7P3R chess engine data with Firebase Storage bucket
# Author: Chess Engine Metrics Agent
# Date: $(date)

set -e  # Exit on any error

# Configuration
PROJECT_ID="chess-engine-metrics-agent"
BUCKET_NAME="chess-engine-metrics-agent.firebasestorage.app"
LOCAL_DATA_ROOT="../raw_data"
BUCKET_ROOT="gs://${BUCKET_NAME}"

# Color output for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== V7P3R Chess Engine Data Sync ===${NC}"
echo "Project: ${PROJECT_ID}"
echo "Bucket: ${BUCKET_NAME}"
echo "Local Data Root: ${LOCAL_DATA_ROOT}"
echo ""

# Function to check if gsutil is available and authenticated
check_gsutil() {
    echo -e "${YELLOW}Checking gsutil authentication...${NC}"
    
    if ! command -v gsutil &> /dev/null; then
        echo -e "${RED}Error: gsutil not found. Please install Google Cloud SDK.${NC}"
        exit 1
    fi
    
    if ! gsutil ls gs://${BUCKET_NAME} &> /dev/null; then
        echo -e "${RED}Error: Cannot access bucket gs://${BUCKET_NAME}${NC}"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    
    echo -e "${GREEN}✓ gsutil authenticated and bucket accessible${NC}"
}

# Function to perform dry run
dry_run_sync() {
    echo -e "${YELLOW}Performing dry run to see what would be synced...${NC}"
    echo ""
    
    echo -e "${BLUE}--- V7P3R Analysis Results (JSON files) ---${NC}"
    gsutil -m rsync -r -n -c \
        "${LOCAL_DATA_ROOT}/analysis_results/v7p3r_analysis/" \
        "${BUCKET_ROOT}/raw-data/analysis-results/v7p3r/"
    
    echo ""
    echo -e "${BLUE}--- Game Records (PGN files) ---${NC}"
    gsutil -m rsync -r -n -c \
        "${LOCAL_DATA_ROOT}/game_records/" \
        "${BUCKET_ROOT}/raw-data/game-records/"
    
    echo ""
    echo -e "${YELLOW}Dry run complete. Use --execute to perform actual sync.${NC}"
}

# Function to perform actual sync
execute_sync() {
    echo -e "${YELLOW}Executing actual sync...${NC}"
    echo ""
    
    # Sync V7P3R analysis results
    echo -e "${BLUE}Syncing V7P3R Analysis Results...${NC}"
    gsutil -m rsync -r -c -d \
        "${LOCAL_DATA_ROOT}/analysis_results/v7p3r_analysis/" \
        "${BUCKET_ROOT}/raw-data/analysis-results/v7p3r/"
    
    echo ""
    
    # Sync game records
    echo -e "${BLUE}Syncing Game Records...${NC}"
    gsutil -m rsync -r -c -d \
        "${LOCAL_DATA_ROOT}/game_records/" \
        "${BUCKET_ROOT}/raw-data/game-records/"
    
    echo ""
    echo -e "${GREEN}✓ Sync completed successfully!${NC}"
    
    # Show summary
    echo ""
    echo -e "${BLUE}=== Sync Summary ===${NC}"
    echo "V7P3R Analysis Results: ${BUCKET_ROOT}/raw-data/analysis-results/v7p3r/"
    echo "Game Records: ${BUCKET_ROOT}/raw-data/game-records/"
}

# Function to show bucket contents
show_bucket_contents() {
    echo -e "${BLUE}=== Current Bucket Contents ===${NC}"
    gsutil ls -r "${BUCKET_ROOT}/raw-data/" || echo "No raw-data directory found in bucket"
}

# Main execution logic
main() {
    check_gsutil
    
    case "${1:-dry-run}" in
        "dry-run"|"--dry-run"|"-n")
            dry_run_sync
            ;;
        "execute"|"--execute"|"-x")
            echo -e "${YELLOW}Are you sure you want to sync data to the bucket? (y/N)${NC}"
            read -r confirmation
            if [[ "$confirmation" =~ ^[Yy]$ ]]; then
                execute_sync
            else
                echo "Sync cancelled."
                exit 0
            fi
            ;;
        "status"|"--status"|"-s")
            show_bucket_contents
            ;;
        "help"|"--help"|"-h")
            echo "Usage: $0 [dry-run|execute|status|help]"
            echo ""
            echo "Commands:"
            echo "  dry-run   : Show what would be synced (default)"
            echo "  execute   : Perform actual sync"
            echo "  status    : Show current bucket contents"
            echo "  help      : Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Dry run"
            echo "  $0 --execute          # Execute sync"
            echo "  $0 --status           # Check bucket"
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Check if local data directories exist
if [ ! -d "${LOCAL_DATA_ROOT}/analysis_results/v7p3r_analysis" ]; then
    echo -e "${RED}Error: V7P3R analysis directory not found: ${LOCAL_DATA_ROOT}/analysis_results/v7p3r_analysis${NC}"
    exit 1
fi

if [ ! -d "${LOCAL_DATA_ROOT}/game_records" ]; then
    echo -e "${RED}Error: Game records directory not found: ${LOCAL_DATA_ROOT}/game_records${NC}"
    exit 1
fi

# Run main function with all arguments
main "$@"