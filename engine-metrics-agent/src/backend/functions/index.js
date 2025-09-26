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

// TODO: Add ETL functions after fixing storage trigger syntax
// const { 
//   consolidateELOData 
// } = require('./v7p3r-etl');
// exports.consolidateELOData = consolidateELOData;

console.log('✅ Functions with V7P3R data migration loaded successfully');