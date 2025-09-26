const functions = require('firebase-functions');
const admin = require('firebase-admin');
const { Storage } = require('@google-cloud/storage');
const fs = require('fs');
const path = require('path');

const storage = new Storage();
const bucket = storage.bucket('chess-engine-metrics-agent.firebasestorage.app');

/**
 * V7P3R Chess Engine Data Migration Service
 * Migrates local raw_data/ to Firebase Storage with intelligent organization
 */

/**
 * Upload local raw_data files to Firebase Storage
 * Organized for V7P3R analysis pipeline
 */
exports.migrateRawData = functions.https.onRequest(async (req, res) => {
  try {
    const { dataType, filePath, targetPath } = req.body;
    
    // Validate input
    if (!dataType || !filePath) {
      return res.status(400).json({
        error: 'Missing required fields: dataType and filePath'
      });
    }

    // Define storage paths based on data type
    const storagePaths = {
      'game_records': 'raw-data/game-records/',
      'v7p3r_analysis': 'raw-data/analysis-results/v7p3r/',
      'dev_docs': 'raw-data/dev-docs/v7p3r/',
      'tournament_results': 'raw-data/tournament-results/'
    };

    const storagePrefix = storagePaths[dataType] || 'raw-data/misc/';
    const finalPath = targetPath || path.basename(filePath);
    const destination = `${storagePrefix}${finalPath}`;

    // Check if file exists locally
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({
        error: `File not found: ${filePath}`
      });
    }

    // Get file stats
    const stats = fs.statSync(filePath);
    
    // Upload to Firebase Storage
    const file = bucket.file(destination);
    await bucket.upload(filePath, {
      destination: destination,
      metadata: {
        metadata: {
          dataType: dataType,
          originalPath: filePath,
          uploadDate: new Date().toISOString(),
          fileSize: stats.size,
          source: 'v7p3r-migration'
        }
      }
    });

    // Log to Firestore for tracking
    await admin.firestore().collection('migrations').add({
      fileName: finalPath,
      dataType: dataType,
      originalPath: filePath,
      storagePath: destination,
      fileSize: stats.size,
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
      status: 'completed'
    });

    res.status(200).json({
      message: 'File uploaded successfully',
      destination: destination,
      size: stats.size,
      type: dataType
    });

  } catch (error) {
    console.error('Migration error:', error);
    res.status(500).json({
      error: 'Upload failed',
      details: error.message
    });
  }
});

/**
 * Bulk migrate an entire directory
 */
exports.migrateBulkData = functions.https.onRequest({
  timeoutSeconds: 540,
  memory: '1GB'
}, async (req, res) => {
    try {
      const { sourceDir, dataType } = req.body;
      
      if (!sourceDir || !dataType) {
        return res.status(400).json({
          error: 'Missing required fields: sourceDir and dataType'
        });
      }

      const results = [];
      const errors = [];

      // Recursively process directory
      const processDirectory = async (dirPath, relativePath = '') => {
        const items = fs.readdirSync(dirPath);
        
        for (const item of items) {
          const itemPath = path.join(dirPath, item);
          const itemRelativePath = path.join(relativePath, item);
          
          const stats = fs.statSync(itemPath);
          
          if (stats.isDirectory()) {
            // Recursively process subdirectory
            await processDirectory(itemPath, itemRelativePath);
          } else {
            try {
              // Upload file
              const storagePath = `raw-data/${dataType}/${itemRelativePath}`;
              const file = bucket.file(storagePath);
              
              await bucket.upload(itemPath, {
                destination: storagePath,
                metadata: {
                  metadata: {
                    dataType: dataType,
                    originalPath: itemPath,
                    uploadDate: new Date().toISOString(),
                    fileSize: stats.size,
                    source: 'bulk-migration'
                  }
                }
              });

              results.push({
                file: itemRelativePath,
                size: stats.size,
                destination: storagePath
              });

            } catch (error) {
              console.error(`Error uploading ${itemPath}:`, error);
              errors.push({
                file: itemRelativePath,
                error: error.message
              });
            }
          }
        }
      };

      await processDirectory(sourceDir);

      // Log bulk migration to Firestore
      await admin.firestore().collection('bulk_migrations').add({
        sourceDirectory: sourceDir,
        dataType: dataType,
        filesUploaded: results.length,
        errors: errors.length,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
        results: results.slice(0, 10), // Store first 10 for reference
        errorSample: errors.slice(0, 5) // Store first 5 errors
      });

      res.status(200).json({
        message: 'Bulk migration completed',
        totalFiles: results.length,
        errors: errors.length,
        summary: results.slice(0, 5), // Show first 5 files
        errorSample: errors.slice(0, 3) // Show first 3 errors
      });

    } catch (error) {
      console.error('Bulk migration error:', error);
      res.status(500).json({
        error: 'Bulk migration failed',
        details: error.message
      });
    }
  });

/**
 * List files in storage for verification
 */
exports.listStorageFiles = functions.https.onRequest(async (req, res) => {
  try {
    const { prefix } = req.query;
    const [files] = await bucket.getFiles({
      prefix: prefix || 'raw-data/'
    });

    const fileList = files.map(file => ({
      name: file.name,
      size: file.metadata.size,
      updated: file.metadata.updated,
      contentType: file.metadata.contentType
    }));

    res.status(200).json({
      files: fileList,
      count: fileList.length,
      prefix: prefix || 'raw-data/'
    });

  } catch (error) {
    console.error('List files error:', error);
    res.status(500).json({
      error: 'Failed to list files',
      details: error.message
    });
  }
});

/**
 * Get migration status and statistics
 */
exports.getMigrationStatus = functions.https.onRequest(async (req, res) => {
  try {
    // Get migration logs from Firestore
    const migrationsSnapshot = await admin.firestore()
      .collection('migrations')
      .orderBy('timestamp', 'desc')
      .limit(50)
      .get();

    const bulkMigrationsSnapshot = await admin.firestore()
      .collection('bulk_migrations')
      .orderBy('timestamp', 'desc')
      .limit(10)
      .get();

    const migrations = migrationsSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    const bulkMigrations = bulkMigrationsSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    // Calculate statistics
    const totalFiles = migrations.length;
    const totalSize = migrations.reduce((sum, m) => sum + (m.fileSize || 0), 0);
    const dataTypes = [...new Set(migrations.map(m => m.dataType))];

    res.status(200).json({
      summary: {
        totalFiles,
        totalSize,
        dataTypes,
        recentMigrations: migrations.slice(0, 10)
      },
      bulkOperations: bulkMigrations,
      lastUpdated: new Date().toISOString()
    });

  } catch (error) {
    console.error('Status error:', error);
    res.status(500).json({
      error: 'Failed to get migration status',
      details: error.message
    });
  }
});