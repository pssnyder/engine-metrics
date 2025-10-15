// V7P3R Lichess Data Collector - Firebase Function
// Automated daily collection of v7p3r_bot games and performance data

const functions = require('firebase-functions');
const admin = require('firebase-admin');
const fetch = require('node-fetch');

// Initialize Firebase Admin
if (admin.apps.length === 0) {
  admin.initializeApp();
}

const db = admin.firestore();
const storage = admin.storage();

// Configuration
const LICHESS_TOKEN = "lip_1vCANjDGz9euqYAcXwy7";
const BOT_USERNAME = "v7p3r_bot";
const LICHESS_BASE_URL = "https://lichess.org/api";

/**
 * Daily scheduled function to collect v7p3r_bot data
 * Triggered every day at 2 AM UTC
 */
exports.collectV7P3RData = functions.pubsub
  .schedule('0 2 * * *')
  .timeZone('UTC')
  .onRun(async (context) => {
    console.log('🤖 Starting V7P3R daily data collection...');
    
    try {
      // Collect daily game data
      const games = await fetchRecentGames(30); // Last 30 games
      const profile = await fetchBotProfile();
      const performance = await fetchPerformanceStats();
      
      // Store data in Firestore
      const timestamp = new Date();
      const dateKey = timestamp.toISOString().split('T')[0]; // YYYY-MM-DD
      
      // Store daily snapshot
      await db.collection('daily_snapshots').doc(dateKey).set({
        timestamp: timestamp,
        profile: profile,
        performance: performance,
        games_count: games.length,
        ratings: extractRatings(profile),
        last_updated: admin.firestore.FieldValue.serverTimestamp()
      });
      
      // Store individual games
      const batch = db.batch();
      games.forEach(game => {
        const gameRef = db.collection('games').doc(game.id);
        batch.set(gameRef, {
          ...game,
          collected_at: timestamp,
          bot_username: BOT_USERNAME
        }, { merge: true });
      });
      await batch.commit();
      
      // Store PGN files in Cloud Storage
      await storeGamePGNs(games, dateKey);
      
      console.log(`✅ Collection complete: ${games.length} games, profile updated`);
      
      return {
        success: true,
        games_collected: games.length,
        timestamp: timestamp.toISOString()
      };
      
    } catch (error) {
      console.error('❌ Data collection failed:', error);
      throw new functions.https.HttpsError('internal', 'Data collection failed', error.message);
    }
  });

/**
 * Real-time game monitoring webhook
 * Triggered when new games are completed
 */
exports.onNewGame = functions.https.onRequest(async (req, res) => {
  console.log('🎮 New game webhook triggered');
  
  try {
    // Verify webhook source (basic security)
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.includes(LICHESS_TOKEN.substring(0, 10))) {
      return res.status(401).send('Unauthorized');
    }
    
    const gameData = req.body;
    
    // Process new game immediately
    if (gameData && gameData.id) {
      const gameDetails = await fetchGameDetails(gameData.id);
      
      // Store in Firestore
      await db.collection('games').doc(gameData.id).set({
        ...gameDetails,
        collected_at: new Date(),
        real_time: true,
        bot_username: BOT_USERNAME
      });
      
      // Trigger performance analysis
      await analyzeGamePerformance(gameDetails);
      
      console.log(`✅ Real-time game processed: ${gameData.id}`);
    }
    
    res.status(200).send('Game processed');
    
  } catch (error) {
    console.error('❌ Real-time processing failed:', error);
    res.status(500).send('Processing failed');
  }
});

/**
 * Manual data collection trigger
 * HTTP function for testing and manual runs
 */
exports.manualCollectV7P3RData = functions.https.onRequest(async (req, res) => {
  console.log('🔧 Manual data collection triggered');
  
  try {
    const maxGames = parseInt(req.query.max_games || '50');
    
    const games = await fetchRecentGames(maxGames);
    const profile = await fetchBotProfile();
    
    res.json({
      success: true,
      games_collected: games.length,
      current_ratings: extractRatings(profile),
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('❌ Manual collection failed:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * Performance analytics processor
 * Analyzes ELO trends, opening performance, etc.
 */
exports.analyzePerformance = functions.firestore
  .document('games/{gameId}')
  .onCreate(async (snap, context) => {
    const game = snap.data();
    
    if (game.bot_username !== BOT_USERNAME) return;
    
    console.log(`🔍 Analyzing performance for game: ${context.params.gameId}`);
    
    try {
      // Extract analysis data
      const analysis = {
        game_id: context.params.gameId,
        timestamp: game.createdAt || new Date(),
        variant: game.variant,
        speed: game.speed,
        result: determineResult(game),
        rating_change: calculateRatingChange(game),
        opening: extractOpening(game),
        time_management: analyzeTimeUsage(game),
        accuracy: calculateAccuracy(game)
      };
      
      // Store analysis
      await db.collection('performance_analysis').doc(context.params.gameId).set(analysis);
      
      // Update aggregate statistics
      await updateAggregateStats(analysis);
      
      console.log(`✅ Performance analysis complete for ${context.params.gameId}`);
      
    } catch (error) {
      console.error('❌ Performance analysis failed:', error);
    }
  });

// Helper Functions

async function fetchRecentGames(maxGames = 30) {
  const headers = {
    'Authorization': `Bearer ${LICHESS_TOKEN}`,
    'Accept': 'application/x-ndjson'
  };
  
  const response = await fetch(`${LICHESS_BASE_URL}/games/user/${BOT_USERNAME}?max=${maxGames}&format=json`, {
    headers: headers,
    timeout: 30000
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch games: ${response.status}`);
  }
  
  const ndjsonText = await response.text();
  const games = ndjsonText.trim().split('\n')
    .filter(line => line.trim())
    .map(line => JSON.parse(line));
  
  return games;
}

async function fetchBotProfile() {
  const response = await fetch(`${LICHESS_BASE_URL}/user/${BOT_USERNAME}`, {
    timeout: 10000
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }
  
  return await response.json();
}

async function fetchPerformanceStats() {
  const response = await fetch(`${LICHESS_BASE_URL}/user/${BOT_USERNAME}/rating-history`, {
    timeout: 10000
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch performance stats: ${response.status}`);
  }
  
  return await response.json();
}

async function fetchGameDetails(gameId) {
  const headers = {
    'Authorization': `Bearer ${LICHESS_TOKEN}`,
    'Accept': 'application/json'
  };
  
  const response = await fetch(`${LICHESS_BASE_URL}/game/${gameId}`, {
    headers: headers,
    timeout: 10000
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch game details: ${response.status}`);
  }
  
  return await response.json();
}

async function storeGamePGNs(games, dateKey) {
  const bucket = storage.bucket();
  
  for (const game of games) {
    if (game.pgn) {
      const fileName = `game-records/${dateKey}/${game.id}.pgn`;
      const file = bucket.file(fileName);
      
      await file.save(game.pgn, {
        metadata: {
          contentType: 'application/x-chess-pgn',
          metadata: {
            gameId: game.id,
            date: dateKey,
            bot: BOT_USERNAME
          }
        }
      });
    }
  }
}

function extractRatings(profile) {
  const ratings = {};
  const perfs = profile.perfs || {};
  
  for (const [gameType, ratingData] of Object.entries(perfs)) {
    if (ratingData && ratingData.rating) {
      ratings[gameType] = {
        rating: ratingData.rating,
        rd: ratingData.rd,
        prov: ratingData.prov || false
      };
    }
  }
  
  return ratings;
}

function determineResult(game) {
  const players = game.players || {};
  const white = players.white || {};
  const black = players.black || {};
  
  const botColor = white.user?.name === BOT_USERNAME ? 'white' : 'black';
  const winner = game.winner;
  
  if (!winner) return 'draw';
  return winner === botColor ? 'win' : 'loss';
}

function calculateRatingChange(game) {
  // Extract rating changes from game data
  const players = game.players || {};
  const white = players.white || {};
  const black = players.black || {};
  
  const botData = white.user?.name === BOT_USERNAME ? white : black;
  return botData.ratingDiff || 0;
}

function extractOpening(game) {
  return {
    eco: game.opening?.eco || 'Unknown',
    name: game.opening?.name || 'Unknown',
    ply: game.opening?.ply || 0
  };
}

function analyzeTimeUsage(game) {
  const clock = game.clock || {};
  return {
    initial: clock.initial || 0,
    increment: clock.increment || 0,
    total_time: clock.totalTime || 0
  };
}

function calculateAccuracy(game) {
  // Placeholder for accuracy calculation
  // Would require analysis of moves vs engine recommendations
  return {
    estimated: null,
    needs_analysis: true
  };
}

async function analyzeGamePerformance(game) {
  // Real-time performance analysis
  // Could trigger additional processing, notifications, etc.
  console.log(`🎯 Real-time analysis for game: ${game.id}`);
}

async function updateAggregateStats(analysis) {
  // Update rolling averages, win rates, etc.
  const statsRef = db.collection('aggregate_stats').doc('v7p3r_bot');
  
  await statsRef.set({
    last_game: analysis.timestamp,
    last_updated: admin.firestore.FieldValue.serverTimestamp()
  }, { merge: true });
}