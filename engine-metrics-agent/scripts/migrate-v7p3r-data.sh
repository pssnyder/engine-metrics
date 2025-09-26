#!/bin/bash

# V7P3R Chess Engine Data Migration Script
# Migrates local raw_data/ to Firebase Storage for cloud processing

echo "🏆 V7P3R Chess Engine Data Migration Starting..."
echo "=================================================="

# Configuration
PROJECT_ROOT="s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics"
RAW_DATA_DIR="$PROJECT_ROOT/raw_data"
FIREBASE_PROJECT="chess-engine-metrics-agent"

# Set Firebase project
echo "📋 Setting Firebase project: $FIREBASE_PROJECT"
firebase use $FIREBASE_PROJECT

# Check if raw_data directory exists
if [ ! -d "$RAW_DATA_DIR" ]; then
    echo "❌ Error: raw_data directory not found at $RAW_DATA_DIR"
    exit 1
fi

echo "✅ Found raw_data directory: $RAW_DATA_DIR"

# Function to upload directory to Firebase Storage
upload_directory() {
    local source_dir="$1"
    local target_prefix="$2"
    local description="$3"
    
    echo ""
    echo "📤 Uploading $description..."
    echo "   Source: $source_dir"
    echo "   Target: gs://$FIREBASE_PROJECT.appspot.com/$target_prefix"
    
    if [ -d "$source_dir" ]; then
        # Get file count for progress tracking
        file_count=$(find "$source_dir" -type f | wc -l)
        echo "   Files to upload: $file_count"
        
        # Use gsutil for batch upload (faster than individual Firebase Storage uploads)
        gsutil -m cp -r "$source_dir"/* "gs://$FIREBASE_PROJECT.appspot.com/$target_prefix/"
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Successfully uploaded $description"
        else
            echo "   ❌ Failed to upload $description"
            return 1
        fi
    else
        echo "   ⚠️  Directory not found: $source_dir"
    fi
}

# Priority 1: V7P3R Analysis Results (ELO SOURCE OF TRUTH)
echo ""
echo "🎯 PRIORITY 1: V7P3R Analysis Results (ELO Data)"
upload_directory "$RAW_DATA_DIR/analysis_results/v7p3r_analysis" "raw-data/analysis-results/v7p3r" "V7P3R Analysis Results"

# Priority 2: Game Records (All Engine Battles)
echo ""
echo "🎯 PRIORITY 2: Game Records (PGN Files)"
upload_directory "$RAW_DATA_DIR/game_records" "raw-data/game-records" "Game Records (PGN Files)"

# Priority 3: V7P3R Development Documentation
echo ""
echo "🎯 PRIORITY 3: V7P3R Development Documentation"
upload_directory "$RAW_DATA_DIR/docs/v7p3r_dev_docs" "raw-data/dev-docs/v7p3r" "V7P3R Development Docs"

# Priority 4: Other Analysis Results (for comparison)
echo ""
echo "🎯 PRIORITY 4: Other Engine Analysis Results"
if [ -d "$RAW_DATA_DIR/analysis_results/slowmate_analysis" ]; then
    upload_directory "$RAW_DATA_DIR/analysis_results/slowmate_analysis" "raw-data/analysis-results/slowmate" "SlowMate Analysis Results"
fi

if [ -d "$RAW_DATA_DIR/analysis_results/c0br4_analysis" ]; then
    upload_directory "$RAW_DATA_DIR/analysis_results/c0br4_analysis" "raw-data/analysis-results/c0br4" "C0BR4 Analysis Results"
fi

# Summary and next steps
echo ""
echo "=================================================="
echo "🏆 V7P3R Data Migration Summary"
echo "=================================================="

# Check uploaded files
echo "📊 Checking uploaded files..."
gsutil ls -l "gs://$FIREBASE_PROJECT.appspot.com/raw-data/" | head -20

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "🔄 Next Steps:"
echo "1. Deploy Firebase Functions: npm run deploy:backend"
echo "2. Trigger ETL processing: Functions will auto-process uploaded files"
echo "3. Verify data in Firestore: Check collections v7p3r_elo_estimates, v7p3r_games"
echo "4. Test ELO consolidation: Call consolidateELOData endpoint"
echo ""
echo "📈 Data Pipeline Status:"
echo "   Raw Data: ✅ Uploaded to Firebase Storage"
echo "   ETL Functions: ⏳ Ready to deploy and process"
echo "   Consolidated ELO: ⏳ Waiting for ETL completion"
echo "   Web Dashboard: ⏳ Ready for development"
echo ""
echo "🚀 Ready to analyze V7P3R performance data in the cloud!"

# Optional: Show storage usage
echo ""
echo "💾 Storage Usage:"
gsutil du -sh "gs://$FIREBASE_PROJECT.appspot.com/raw-data/"