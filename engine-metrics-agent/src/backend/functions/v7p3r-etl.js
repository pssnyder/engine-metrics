const functions = require('firebase-functions');
const admin = require('firebase-admin');
const { Storage } = require('@google-cloud/storage');

const storage = new Storage();
const bucket = storage.bucket('chess-engine-metrics-agent.firebasestorage.app');
const db = admin.firestore();

/**
 * V7P3R Chess Engine ETL Processing Functions
 * Process raw chess data into structured analytics-ready format
 */

/**
 * Process V7P3R analysis JSON files (ELO SOURCE OF TRUTH)
 * Triggers on new files in raw-data/analysis-results/v7p3r/
 */
/**
 * Process V7P3R analysis JSON files (ELO SOURCE OF TRUTH)
 * Triggers on new files in raw-data/analysis-results/v7p3r/
 */
exports.processV7P3RAnalysis = functions
  .runWith({ timeoutSeconds: 300, memory: '512MB' })
  .storage.object().onFinalize(async (object) => {
  try {
    // Only process V7P3R analysis files
    if (!object.name.includes('analysis-results/v7p3r/') || 
        !object.name.includes('enhanced_sequence_analysis') ||
        !object.name.endsWith('.json')) {
      console.log('Skipping non-V7P3R analysis file:', object.name);
      return;
    }

    console.log('Processing V7P3R analysis file:', object.name);

    // Download and parse the JSON file
    const file = bucket.file(object.name);
    const [data] = await file.download();
    const analysisData = JSON.parse(data.toString());

    // Extract key metrics
    const processedData = {
      fileName: object.name.split('/').pop(),
      uploadDate: object.timeCreated,
      fileSize: parseInt(object.size),
      
      // Extract ELO data (PRIMARY SOURCE OF TRUTH)
      eloData: extractELOData(analysisData),
      
      // Extract puzzle performance
      puzzleMetrics: extractPuzzleMetrics(analysisData),
      
      // Extract engine version info
      versionInfo: extractVersionInfo(analysisData),
      
      // Calculate weighted scores (prioritize high sample size)
      weightedScores: calculateWeightedScores(analysisData),
      
      // Processing metadata
      processedAt: admin.firestore.FieldValue.serverTimestamp(),
      source: 'v7p3r-analysis-etl'
    };

    // Store in Firestore - ELO estimates collection
    const docId = `${processedData.versionInfo.version}_${Date.now()}`;
    await db.collection('v7p3r_elo_estimates').doc(docId).set(processedData);

    // Update consolidated ELO tracking
    await updateConsolidatedELO(processedData);

    console.log('✅ Successfully processed V7P3R analysis:', docId);
    
    return { success: true, documentId: docId };

  } catch (error) {
    console.error('❌ Error processing V7P3R analysis:', error);
    throw error;
  }
});

/**
 * Process PGN game files (ignore embedded ELO, focus on game outcomes)
 * Triggers on new PGN files in raw-data/game-records/
 */
exports.processGameRecords = functions
  .runWith({ timeoutSeconds: 300, memory: '512MB' })
  .storage.object().onFinalize(async (object) => {
  try {
    // Only process PGN files
    if (!object.name.includes('game-records/') || !object.name.endsWith('.pgn')) {
      console.log('Skipping non-PGN file:', object.name);
      return;
    }

    console.log('Processing PGN file:', object.name);

    // Download and parse PGN
    const file = bucket.file(object.name);
    const [data] = await file.download();
    const pgnContent = data.toString();

    // Parse PGN games
    const games = parsePGNGames(pgnContent);
    
    // Process each game
    const processedGames = games.map(game => ({
      ...game,
      fileName: object.name.split('/').pop(),
      uploadDate: object.timeCreated,
      
      // Calculate game-based ELO (for validation against analysis ELO)
      gameBasedELO: calculateGameELO(game),
      
      // Extract tournament info
      tournamentInfo: extractTournamentInfo(object.name),
      
      // IGNORE embedded PGN ELO values
      embeddedELOIgnored: true,
      
      processedAt: admin.firestore.FieldValue.serverTimestamp(),
      source: 'pgn-etl'
    }));

    // Batch write to Firestore
    const batch = db.batch();
    processedGames.forEach((game, index) => {
      const docId = `${game.tournamentInfo.date}_game_${index}`;
      const ref = db.collection('v7p3r_games').doc(docId);
      batch.set(ref, game);
    });

    await batch.commit();

    console.log(`✅ Successfully processed ${processedGames.length} games from ${object.name}`);
    
    return { success: true, gamesProcessed: processedGames.length };

  } catch (error) {
    console.error('❌ Error processing PGN file:', error);
    throw error;
  }
});

/**
 * Consolidate ELO data from multiple sources
 * Manual trigger for ELO consolidation
 */
exports.consolidateELOData = functions.https.onRequest(async (req, res) => {
  try {
    console.log('Starting ELO consolidation process...');

    // Get all V7P3R analysis data (primary ELO source)
    const analysisSnapshot = await db.collection('v7p3r_elo_estimates')
      .orderBy('processedAt', 'desc')
      .get();

    // Get all game results (for validation ELO)
    const gamesSnapshot = await db.collection('v7p3r_games')
      .where('engines', 'array-contains', 'V7P3R')
      .get();

    const analysisData = analysisSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    const gameData = gamesSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    // Consolidate ELO by version and date
    const consolidatedELO = await consolidateELOByVersion(analysisData, gameData);

    // Store consolidated results
    const consolidationDoc = {
      consolidatedAt: admin.firestore.FieldValue.serverTimestamp(),
      eloProgression: consolidatedELO,
      dataSources: {
        analysisFiles: analysisData.length,
        gameRecords: gameData.length
      },
      methodology: {
        primarySource: 'v7p3r-analysis-json',
        validationSource: 'game-outcomes',
        weightingStrategy: 'sample-size-weighted'
      }
    };

    await db.collection('v7p3r_consolidated_elo')
      .doc(`consolidation_${Date.now()}`)
      .set(consolidationDoc);

    res.status(200).json({
      success: true,
      message: 'ELO consolidation completed',
      versionsProcessed: Object.keys(consolidatedELO).length,
      totalAnalysisFiles: analysisData.length,
      totalGames: gameData.length
    });

  } catch (error) {
    console.error('❌ ELO consolidation error:', error);
    res.status(500).json({
      error: 'ELO consolidation failed',
      details: error.message
    });
  }
});

// Helper Functions

function extractELOData(analysisData) {
  // Extract ELO estimates from V7P3R analysis JSON
  const eloPattern = /elo[:\s]+(\d+)/gi;
  const content = JSON.stringify(analysisData);
  const matches = content.match(eloPattern);
  
  if (matches && matches.length > 0) {
    const eloValues = matches.map(match => parseInt(match.replace(/\D/g, '')));
    return {
      estimates: eloValues,
      average: eloValues.reduce((a, b) => a + b, 0) / eloValues.length,
      range: {
        min: Math.min(...eloValues),
        max: Math.max(...eloValues)
      },
      confidence: calculateELOConfidence(analysisData)
    };
  }
  
  return null;
}

function extractPuzzleMetrics(analysisData) {
  // Extract puzzle-solving performance metrics
  const puzzleCount = analysisData.puzzlesSolved || 0;
  const accuracy = analysisData.accuracy || 0;
  
  return {
    totalPuzzles: puzzleCount,
    accuracy: accuracy,
    weightFactor: Math.min(puzzleCount / 1000, 1.0), // Higher weight for more puzzles
    tacticalStrength: accuracy * (puzzleCount / 100) // Composite metric
  };
}

function extractVersionInfo(analysisData) {
  // Extract V7P3R version information
  const versionPattern = /v(\d+\.\d+)/i;
  const content = JSON.stringify(analysisData);
  const match = content.match(versionPattern);
  
  return {
    version: match ? match[0] : 'unknown',
    majorVersion: match ? parseInt(match[1].split('.')[0]) : 0,
    minorVersion: match ? parseInt(match[1].split('.')[1]) : 0
  };
}

function calculateWeightedScores(analysisData) {
  // Calculate weighted scores prioritizing high sample sizes
  const puzzleCount = analysisData.puzzlesSolved || 1;
  const baseWeight = Math.log(puzzleCount + 1) / Math.log(10); // Logarithmic weighting
  
  return {
    sampleSize: puzzleCount,
    weightFactor: baseWeight,
    reliability: puzzleCount > 100 ? 'high' : puzzleCount > 50 ? 'medium' : 'low'
  };
}

function parsePGNGames(pgnContent) {
  // Parse PGN format and extract games
  const games = [];
  const gamePattern = /\[([^\]]+)\]\s*\n([^[]*)/g;
  let match;
  
  while ((match = gamePattern.exec(pgnContent)) !== null) {
    const headers = parseHeaders(match[1]);
    const moves = match[2].trim();
    
    games.push({
      headers: headers,
      moves: moves,
      result: headers.Result || '*',
      engines: [headers.White, headers.Black].filter(e => e), 
      date: headers.Date,
      // EXPLICITLY IGNORE PGN ELO VALUES
      pgnELOIgnored: {
        whiteELO: headers.WhiteELO, // Store but don't use
        blackELO: headers.BlackELO   // Store but don't use
      }
    });
  }
  
  return games;
}

function parseHeaders(headerString) {
  // Parse PGN headers into object
  const headers = {};
  const headerPattern = /(\w+)\s+"([^"]+)"/g;
  let match;
  
  while ((match = headerPattern.exec(headerString)) !== null) {
    headers[match[1]] = match[2];
  }
  
  return headers;
}

function calculateGameELO(game) {
  // Calculate ELO based on game outcomes using BayesElo-style calculation
  // This is for validation against analysis-based ELO
  
  const result = game.result;
  let performance = 0.5; // Default draw
  
  if (result === '1-0' && game.engines[0] === 'V7P3R') performance = 1.0;
  else if (result === '0-1' && game.engines[1] === 'V7P3R') performance = 1.0;
  else if (result === '1-0' && game.engines[1] === 'V7P3R') performance = 0.0;
  else if (result === '0-1' && game.engines[0] === 'V7P3R') performance = 0.0;
  
  return {
    performance: performance,
    opponent: game.engines.find(e => e !== 'V7P3R') || 'unknown',
    calculatedFor: 'validation-only' // Don't use as primary ELO source
  };
}

function extractTournamentInfo(fileName) {
  // Extract tournament date and info from file path
  const datePattern = /(\d{8})/;
  const match = fileName.match(datePattern);
  
  return {
    date: match ? match[1] : 'unknown',
    tournament: fileName.split('/').pop().replace('.pgn', ''),
    source: 'engine-battle'
  };
}

async function updateConsolidatedELO(processedData) {
  // Update the consolidated ELO tracking document
  const version = processedData.versionInfo.version;
  const docRef = db.collection('v7p3r_elo_progression').doc(version);
  
  await docRef.set({
    version: version,
    latestELO: processedData.eloData?.average || null,
    eloRange: processedData.eloData?.range || null,
    puzzleMetrics: processedData.puzzleMetrics,
    lastUpdated: admin.firestore.FieldValue.serverTimestamp(),
    reliability: processedData.weightedScores?.reliability || 'unknown'
  }, { merge: true });
}

async function consolidateELOByVersion(analysisData, gameData) {
  // Consolidate ELO data by version with weighting
  const consolidated = {};
  
  // Group analysis data by version
  analysisData.forEach(data => {
    const version = data.versionInfo?.version || 'unknown';
    
    if (!consolidated[version]) {
      consolidated[version] = {
        version: version,
        eloEstimates: [],
        gamePerformance: [],
        weightedAverage: 0,
        confidence: 'low'
      };
    }
    
    if (data.eloData?.average) {
      consolidated[version].eloEstimates.push({
        value: data.eloData.average,
        weight: data.weightedScores?.weightFactor || 1,
        source: 'analysis'
      });
    }
  });
  
  // Add game-based ELO for validation
  gameData.forEach(game => {
    // Extract version from game data if available
    const version = 'latest'; // Simplified for now
    
    if (consolidated[version] && game.gameBasedELO) {
      consolidated[version].gamePerformance.push({
        performance: game.gameBasedELO.performance,
        opponent: game.gameBasedELO.opponent,
        source: 'game-outcome'
      });
    }
  });
  
  // Calculate final weighted averages
  Object.keys(consolidated).forEach(version => {
    const data = consolidated[version];
    
    if (data.eloEstimates.length > 0) {
      const totalWeight = data.eloEstimates.reduce((sum, est) => sum + est.weight, 0);
      const weightedSum = data.eloEstimates.reduce((sum, est) => sum + (est.value * est.weight), 0);
      data.weightedAverage = Math.round(weightedSum / totalWeight);
      data.confidence = totalWeight > 5 ? 'high' : totalWeight > 2 ? 'medium' : 'low';
    }
  });
  
  return consolidated;
}

function calculateELOConfidence(analysisData) {
  // Calculate confidence in ELO estimate based on data quality
  const sampleSize = analysisData.puzzlesSolved || 0;
  const accuracy = analysisData.accuracy || 0;
  
  if (sampleSize > 1000 && accuracy > 0.9) return 'very-high';
  if (sampleSize > 500 && accuracy > 0.8) return 'high';
  if (sampleSize > 100 && accuracy > 0.7) return 'medium';
  return 'low';
}

module.exports = {
  extractELOData,
  extractPuzzleMetrics,
  parsePGNGames,
  calculateWeightedScores
};