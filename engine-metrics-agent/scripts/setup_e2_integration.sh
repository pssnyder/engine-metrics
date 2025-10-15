#!/bin/bash
# V7P3R E2 Instance Data Stream Setup
# Configures automatic data streaming from the production bot instance to Firebase

set -e

# Configuration
E2_INSTANCE="v7p3r-production-bot"
E2_ZONE="us-central1-a"
E2_PROJECT="v7p3r-lichess-bot"
FIREBASE_PROJECT="chess-engine-metrics-agent"
BUCKET_NAME="chess-engine-metrics-agent.firebasestorage.app"

echo "🔧 V7P3R E2 Instance Integration Setup"
echo "================================="
echo "E2 Instance: ${E2_INSTANCE}"
echo "Zone: ${E2_ZONE}"
echo "Project: ${E2_PROJECT}"
echo "Target Firebase: ${FIREBASE_PROJECT}"
echo ""

# Function to check if we can access the E2 instance
check_e2_access() {
    echo "🔍 Checking E2 instance access..."
    
    if gcloud compute instances describe "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" &>/dev/null; then
        echo "✅ E2 instance accessible"
        return 0
    else
        echo "❌ Cannot access E2 instance"
        echo "💡 You may need to:"
        echo "   1. Authenticate: gcloud auth login"
        echo "   2. Set project: gcloud config set project ${E2_PROJECT}"
        echo "   3. Enable Compute Engine API"
        return 1
    fi
}

# Function to check current data on E2 instance
check_e2_data() {
    echo "📁 Checking data structure on E2 instance..."
    
    gcloud compute ssh "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" \
        --command="
            echo '=== V7P3R Bot Data Discovery ==='
            echo 'Home directory structure:'
            ls -la /home/v7p3r/ 2>/dev/null || echo 'No /home/v7p3r directory'
            
            echo -e '\nLooking for game records:'
            find /home -name '*.pgn' 2>/dev/null | head -5
            find /home -name '*.json' -path '*game*' 2>/dev/null | head -5
            
            echo -e '\nContainer status:'
            docker ps -a | grep v7p3r || echo 'No v7p3r containers found'
            
            echo -e '\nDocker logs (last 10 lines):'
            docker logs \$(docker ps -q | head -1) 2>/dev/null | tail -10 || echo 'No recent container logs'
            
            echo -e '\nDisk usage:'
            df -h /home
        " 2>/dev/null || {
        echo "❌ Could not connect to E2 instance"
        echo "💡 This might be due to:"
        echo "   1. SSH key not configured"
        echo "   2. Firewall restrictions"
        echo "   3. Instance not running"
        return 1
    }
}

# Function to set up data streaming from E2 to Firebase
setup_data_streaming() {
    echo "📡 Setting up data streaming from E2 to Firebase..."
    
    # Create the streaming script on the E2 instance
    gcloud compute ssh "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" \
        --command="
            # Create data sync script
            cat > /home/v7p3r/sync_to_firebase.sh << 'SYNC_SCRIPT'
#!/bin/bash
# V7P3R Data Sync to Firebase Storage
# Runs every hour to sync game data

BUCKET_URL='gs://${BUCKET_NAME}'
LOCAL_GAME_DIR='/home/v7p3r/game_records'
LOCAL_LOG_DIR='/home/v7p3r/logs'
DATE=\$(date +%Y%m%d_%H%M%S)

echo \"\$(date): Starting Firebase sync...\" >> /home/v7p3r/sync.log

# Sync game records if they exist
if [ -d \"\$LOCAL_GAME_DIR\" ] && [ \"\$(ls -A \$LOCAL_GAME_DIR)\" ]; then
    echo \"Syncing game records...\" >> /home/v7p3r/sync.log
    gsutil -m rsync -r -c \"\$LOCAL_GAME_DIR/\" \"\$BUCKET_URL/e2-instance-data/game-records/\"
    echo \"Game records synced\" >> /home/v7p3r/sync.log
fi

# Sync logs
if [ -d \"\$LOCAL_LOG_DIR\" ] && [ \"\$(ls -A \$LOCAL_LOG_DIR)\" ]; then
    echo \"Syncing logs...\" >> /home/v7p3r/sync.log
    gsutil -m rsync -r -c \"\$LOCAL_LOG_DIR/\" \"\$BUCKET_URL/e2-instance-data/logs/\"
    echo \"Logs synced\" >> /home/v7p3r/sync.log
fi

# Sync Docker container data
if docker ps -q | head -1 >/dev/null; then
    CONTAINER_ID=\$(docker ps -q | head -1)
    echo \"Backing up container data...\" >> /home/v7p3r/sync.log
    
    # Export recent container logs
    docker logs --since=24h \"\$CONTAINER_ID\" > \"/tmp/container_logs_\$DATE.log\" 2>&1
    gsutil cp \"/tmp/container_logs_\$DATE.log\" \"\$BUCKET_URL/e2-instance-data/container-logs/\"
    rm \"/tmp/container_logs_\$DATE.log\"
    
    echo \"Container data backed up\" >> /home/v7p3r/sync.log
fi

echo \"\$(date): Firebase sync completed\" >> /home/v7p3r/sync.log

# Keep sync log manageable (last 1000 lines)
tail -1000 /home/v7p3r/sync.log > /home/v7p3r/sync.log.tmp
mv /home/v7p3r/sync.log.tmp /home/v7p3r/sync.log
SYNC_SCRIPT

            # Make script executable
            chmod +x /home/v7p3r/sync_to_firebase.sh
            chown v7p3r:v7p3r /home/v7p3r/sync_to_firebase.sh
            
            echo '✅ Sync script created at /home/v7p3r/sync_to_firebase.sh'
        " || {
        echo "❌ Failed to create sync script on E2 instance"
        return 1
    }
}

# Function to set up automatic sync schedule
setup_sync_schedule() {
    echo "⏰ Setting up automatic sync schedule..."
    
    gcloud compute ssh "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" \
        --command="
            # Add hourly sync to crontab
            (crontab -u v7p3r -l 2>/dev/null || echo '') | grep -v 'sync_to_firebase.sh' > /tmp/crontab_temp
            echo '0 * * * * /home/v7p3r/sync_to_firebase.sh' >> /tmp/crontab_temp
            crontab -u v7p3r /tmp/crontab_temp
            rm /tmp/crontab_temp
            
            echo '✅ Hourly sync scheduled in crontab'
            echo 'Current crontab for v7p3r:'
            crontab -u v7p3r -l
        " || {
        echo "❌ Failed to set up sync schedule"
        return 1
    }
}

# Function to test the sync setup
test_sync() {
    echo "🧪 Testing data sync..."
    
    gcloud compute ssh "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" \
        --command="
            echo 'Testing sync script...'
            sudo -u v7p3r /home/v7p3r/sync_to_firebase.sh
            
            echo -e '\nChecking sync log:'
            tail -5 /home/v7p3r/sync.log
        " || {
        echo "❌ Sync test failed"
        return 1
    }
    
    echo "✅ Sync test completed"
}

# Function to create monitoring script
setup_monitoring() {
    echo "📊 Setting up E2 instance monitoring..."
    
    gcloud compute ssh "$E2_INSTANCE" \
        --zone="$E2_ZONE" \
        --project="$E2_PROJECT" \
        --command="
            cat > /home/v7p3r/monitor_bot.sh << 'MONITOR_SCRIPT'
#!/bin/bash
# V7P3R Bot Monitoring Script
# Reports bot status to Firebase

BUCKET_URL='gs://${BUCKET_NAME}'
TIMESTAMP=\$(date -Iseconds)
STATUS_FILE=\"/tmp/bot_status_\$(date +%Y%m%d_%H%M%S).json\"

# Collect system status
cat > \"\$STATUS_FILE\" << STATUS_JSON
{
  \"timestamp\": \"\$TIMESTAMP\",
  \"instance\": \"${E2_INSTANCE}\",
  \"uptime\": \"\$(uptime)\",
  \"memory_usage\": \"\$(free -h | grep Mem)\",
  \"disk_usage\": \"\$(df -h /home | tail -1)\",
  \"docker_status\": {
    \"containers_running\": \$(docker ps -q | wc -l),
    \"containers_total\": \$(docker ps -a -q | wc -l)
  },
  \"network_status\": \"\$(ping -c 1 lichess.org > /dev/null 2>&1 && echo 'online' || echo 'offline')\",
  \"bot_process\": \"\$(ps aux | grep -i v7p3r | grep -v grep | wc -l)\"
}
STATUS_JSON

# Upload status to Firebase
gsutil cp \"\$STATUS_FILE\" \"\$BUCKET_URL/e2-instance-data/status/\"
rm \"\$STATUS_FILE\"
MONITOR_SCRIPT

            chmod +x /home/v7p3r/monitor_bot.sh
            chown v7p3r:v7p3r /home/v7p3r/monitor_bot.sh
            
            # Add to crontab (every 15 minutes)
            (crontab -u v7p3r -l 2>/dev/null || echo '') | grep -v 'monitor_bot.sh' > /tmp/crontab_temp
            echo '*/15 * * * * /home/v7p3r/monitor_bot.sh' >> /tmp/crontab_temp
            crontab -u v7p3r /tmp/crontab_temp
            rm /tmp/crontab_temp
            
            echo '✅ Monitoring script created and scheduled'
        " || {
        echo "❌ Failed to set up monitoring"
        return 1
    }
}

# Main execution
main() {
    echo "Starting E2 instance integration setup..."
    
    # Check prerequisites
    if ! command -v gcloud &> /dev/null; then
        echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Execute setup steps
    check_e2_access || exit 1
    check_e2_data || exit 1
    setup_data_streaming || exit 1
    setup_sync_schedule || exit 1
    setup_monitoring || exit 1
    test_sync || exit 1
    
    echo ""
    echo "🎉 E2 Instance Integration Complete!"
    echo "================================="
    echo "✅ Data sync script installed and scheduled"
    echo "✅ Monitoring script running every 15 minutes"
    echo "✅ Game data will sync hourly to Firebase Storage"
    echo ""
    echo "📊 Monitor the integration:"
    echo "   Firebase Storage: gs://${BUCKET_NAME}/e2-instance-data/"
    echo "   Sync logs: /home/v7p3r/sync.log on E2 instance"
    echo ""
    echo "🔧 Manual operations:"
    echo "   Test sync: gcloud compute ssh ${E2_INSTANCE} --zone=${E2_ZONE} --project=${E2_PROJECT} --command='/home/v7p3r/sync_to_firebase.sh'"
    echo "   Check status: gcloud compute ssh ${E2_INSTANCE} --zone=${E2_ZONE} --project=${E2_PROJECT} --command='/home/v7p3r/monitor_bot.sh'"
}

# Handle command line arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "check")
        check_e2_access && check_e2_data
        ;;
    "test")
        test_sync
        ;;
    "status")
        gcloud compute ssh "$E2_INSTANCE" --zone="$E2_ZONE" --project="$E2_PROJECT" --command="tail -10 /home/v7p3r/sync.log"
        ;;
    *)
        echo "Usage: $0 [setup|check|test|status]"
        exit 1
        ;;
esac