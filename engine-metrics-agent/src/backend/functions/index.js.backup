const functions = require('firebase-functions');
const admin = require('firebase-admin');
const cors = require('cors')({ origin: true });

// Initialize Firebase Admin
admin.initializeApp();

// Import function modules
const { uploadHandler } = require('./data-ingestion');
const { processDataWithAI } = require('./ai-processing');
const { handleQuery } = require('./query-handler');

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

// Firestore trigger for new data processing
exports.processNewData = functions.firestore
  .document('uploads/{uploadId}')
  .onCreate(async (snap, context) => {
    const uploadData = snap.data();
    
    try {
      // Process the uploaded file
      const processedData = await processUploadedFile(uploadData);
      
      // Store processed results
      await admin.firestore()
        .collection('analysis')
        .add({
          uploadId: context.params.uploadId,
          processedData: processedData,
          timestamp: admin.firestore.FieldValue.serverTimestamp(),
          status: 'completed'
        });
        
      console.log(`Successfully processed upload: ${context.params.uploadId}`);
    } catch (error) {
      console.error('Error processing upload:', error);
      
      // Store error status
      await admin.firestore()
        .collection('analysis')
        .add({
          uploadId: context.params.uploadId,
          error: error.message,
          timestamp: admin.firestore.FieldValue.serverTimestamp(),
          status: 'failed'
        });
    }
  });

// Helper function to process uploaded files
async function processUploadedFile(uploadData) {
  const { fileName, filePath, fileType, userId } = uploadData;
  
  // Download file from Storage
  const bucket = admin.storage().bucket();
  const file = bucket.file(filePath);
  
  const [fileContents] = await file.download();
  const content = fileContents.toString();
  
  let processedData = {};
  
  // Process based on file type
  switch (fileType) {
    case 'pgn':
      processedData = await processPGNFile(content);
      break;
    case 'json':
      processedData = await processJSONFile(content);
      break;
    case 'md':
      processedData = await processMarkdownFile(content);
      break;
    default:
      throw new Error(`Unsupported file type: ${fileType}`);
  }
  
  return {
    fileName,
    fileType,
    extractedData: processedData,
    userId,
    processedAt: new Date().toISOString()
  };
}

// Process PGN files
async function processPGNFile(content) {
  // Parse PGN content and extract game metadata
  const games = [];
  const pgnBlocks = content.split('\n\n\n').filter(block => block.trim());
  
  for (const block of pgnBlocks) {
    if (block.includes('[Event ')) {
      const game = extractGameMetadata(block);
      if (game) games.push(game);
    }
  }
  
  return {
    type: 'pgn_analysis',
    totalGames: games.length,
    games: games.slice(0, 100), // Limit to first 100 games for processing
    enginePerformance: analyzeEnginePerformance(games)
  };
}

// Process JSON files
async function processJSONFile(content) {
  try {
    const data = JSON.parse(content);
    return {
      type: 'json_analysis',
      data: data,
      insights: extractJSONInsights(data)
    };
  } catch (error) {
    throw new Error(`Invalid JSON format: ${error.message}`);
  }
}

// Process Markdown files
async function processMarkdownFile(content) {
  return {
    type: 'markdown_analysis',
    wordCount: content.split(/\s+/).length,
    sections: extractMarkdownSections(content),
    summary: content.substring(0, 500) + '...'
  };
}

// Helper functions
function extractGameMetadata(pgnBlock) {
  const metadata = {};
  const lines = pgnBlock.split('\n');
  
  for (const line of lines) {
    const match = line.match(/\[(\w+)\s+"([^"]+)"\]/);
    if (match) {
      metadata[match[1]] = match[2];
    }
  }
  
  if (metadata.White && metadata.Black && metadata.Result) {
    return {
      white: metadata.White,
      black: metadata.Black,
      result: metadata.Result,
      date: metadata.Date || 'Unknown',
      event: metadata.Event || 'Unknown',
      timeControl: metadata.TimeControl || 'Unknown'
    };
  }
  
  return null;
}

function analyzeEnginePerformance(games) {
  const engineStats = {};
  
  games.forEach(game => {
    [game.white, game.black].forEach(engine => {
      if (!engineStats[engine]) {
        engineStats[engine] = { wins: 0, losses: 0, draws: 0, total: 0 };
      }
      engineStats[engine].total++;
      
      if (game.result === '1-0') {
        if (engine === game.white) engineStats[engine].wins++;
        else engineStats[engine].losses++;
      } else if (game.result === '0-1') {
        if (engine === game.black) engineStats[engine].wins++;
        else engineStats[engine].losses++;
      } else {
        engineStats[engine].draws++;
      }
    });
  });
  
  return engineStats;
}

function extractJSONInsights(data) {
  // Basic analysis of JSON data structure
  const insights = {
    dataSize: JSON.stringify(data).length,
    topLevelKeys: Object.keys(data),
    dataTypes: {}
  };
  
  for (const [key, value] of Object.entries(data)) {
    insights.dataTypes[key] = Array.isArray(value) ? 'array' : typeof value;
  }
  
  return insights;
}

function extractMarkdownSections(content) {
  const sections = [];
  const lines = content.split('\n');
  
  lines.forEach((line, index) => {
    if (line.startsWith('#')) {
      const level = (line.match(/^#+/) || [''])[0].length;
      const title = line.replace(/^#+\s*/, '');
      sections.push({ level, title, lineNumber: index + 1 });
    }
  });
  
  return sections;
}