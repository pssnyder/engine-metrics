const functions = require('firebase-functions');
const admin = require('firebase-admin');
const cors = require('cors')({ origin: true });

// Initialize Firebase Admin
admin.initializeApp();

// Import function modules one by one to isolate issues
const { uploadHandler } = require('./data-ingestion');
const { processDataWithAI } = require('./ai-processing');
const { handleQuery } = require('./query-handler');
const { getOverallMetrics, getVersionMetrics, processAnalyticsQuery } = require('./analytics-handler');

// Import data processor for dynamic refresh capabilities
const dataProcessor = require('./data-processor');

// Import V7P3R-specific modules
const { 
  migrateRawData, 
  migrateBulkData, 
  listStorageFiles, 
  getMigrationStatus 
} = require('./data-migration');

// Simple health check function
exports.health = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    res.status(200).json({
      message: 'Firebase Functions are healthy!',
      timestamp: new Date().toISOString(),
      project: process.env.GCLOUD_PROJECT
    });
  });
});

// Data upload endpoint
exports.uploadData = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    uploadHandler(req, res);
  });
});

// AI processing endpoint
exports.processAI = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    processDataWithAI(req, res);
  });
});

// Query handling endpoint
exports.query = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    handleQuery(req, res);
  });
});

// Analytics endpoints for V7P3R dashboard
exports.getOverallMetrics = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const metrics = await getOverallMetrics();
      res.status(200).json(metrics);
    } catch (error) {
      console.error('Error getting overall metrics:', error);
      res.status(500).json({ error: 'Failed to fetch overall metrics' });
    }
  });
});

exports.getVersionMetrics = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const version = req.query.version || req.body.version || 'All';
      const metrics = await getVersionMetrics(version);
      res.status(200).json(metrics);
    } catch (error) {
      console.error('Error getting version metrics:', error);
      res.status(500).json({ error: 'Failed to fetch version metrics' });
    }
  });
});

exports.processAnalyticsQuery = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const { query } = req.body;
      if (!query) {
        return res.status(400).json({ error: 'Query is required' });
      }
      
      const response = await processAnalyticsQuery(query);
      res.status(200).json(response);
    } catch (error) {
      console.error('Error processing analytics query:', error);
      res.status(500).json({ error: 'Failed to process analytics query' });
    }
  });
});

// V7P3R Data Migration Endpoints
exports.migrateRawData = migrateRawData;
exports.migrateBulkData = migrateBulkData;
exports.listStorageFiles = listStorageFiles;
exports.getMigrationStatus = getMigrationStatus;

// NEW: Dynamic Refresh and Live Monitoring Endpoints

// Check for new data since last timestamp
exports.checkNewData = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    try {
      const lastChecked = req.query.lastChecked ? parseInt(req.query.lastChecked) : null;
      const result = dataProcessor.checkForNewGameData(lastChecked);
      res.status(200).json(result);
    } catch (error) {
      console.error('Error checking for new data:', error);
      res.status(500).json({ error: 'Failed to check for new data' });
    }
  });
});

// Get current live games (in progress)
exports.getLiveGames = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    try {
      const liveGames = dataProcessor.getCurrentLiveGames();
      res.status(200).json({
        liveGames,
        count: liveGames.length,
        lastUpdated: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error getting live games:', error);
      res.status(500).json({ error: 'Failed to get live games' });
    }
  });
});

// Get recent game statistics
exports.getRecentStats = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    try {
      const daysBack = req.query.days ? parseInt(req.query.days) : 7;
      const stats = dataProcessor.getRecentGameStats(daysBack);
      res.status(200).json(stats || { error: 'No stats available' });
    } catch (error) {
      console.error('Error getting recent stats:', error);
      res.status(500).json({ error: 'Failed to get recent statistics' });
    }
  });
});

// Get available battle dates
exports.getBattleDates = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    try {
      const dates = dataProcessor.getAvailableBattleDates();
      res.status(200).json({
        dates,
        count: dates.length,
        mostRecent: dates.length > 0 ? dates[dates.length - 1] : null
      });
    } catch (error) {
      console.error('Error getting battle dates:', error);
      res.status(500).json({ error: 'Failed to get battle dates' });
    }
  });
});

// Trigger manual metrics refresh
exports.refreshMetrics = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const recentStats = dataProcessor.getRecentGameStats(30); // Last 30 days
      const overallMetrics = await getOverallMetrics();
      
      res.status(200).json({
        message: 'Metrics refreshed successfully',
        refreshedAt: new Date().toISOString(),
        recentStats,
        overallMetrics
      });
    } catch (error) {
      console.error('Error refreshing metrics:', error);
      res.status(500).json({ error: 'Failed to refresh metrics' });
    }
  });
});

// TODO: Add ETL functions after fixing storage trigger syntax
// const { 
//   consolidateELOData 
// } = require('./v7p3r-etl');
// exports.consolidateELOData = consolidateELOData;

console.log('✅ Functions with V7P3R data migration loaded successfully');