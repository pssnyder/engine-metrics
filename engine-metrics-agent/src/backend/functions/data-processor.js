const fs = require('fs');
const path = require('path');

/**
 * Data Processing Service for Real Raw Data
 * This service reads actual tournament data from raw_data folder
 */

const RAW_DATA_PATH = path.join(__dirname, '../../../../../../raw_data');

/**
 * Get list of all available battle dates
 */
const getAvailableBattleDates = () => {
  try {
    const gameRecordsPath = path.join(RAW_DATA_PATH, 'game_records');
    if (!fs.existsSync(gameRecordsPath)) {
      console.warn('Game records path does not exist:', gameRecordsPath);
      return [];
    }

    const directories = fs.readdirSync(gameRecordsPath, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name)
      .filter(name => name.startsWith('Engine Battle'))
      .sort();

    return directories;
  } catch (error) {
    console.error('Error reading battle dates:', error);
    return [];
  }
};

/**
 * Get the most recent battle date for live monitoring
 */
const getMostRecentBattleDate = () => {
  const dates = getAvailableBattleDates();
  return dates.length > 0 ? dates[dates.length - 1] : null;
};

/**
 * Check for new game files in the most recent battle directory
 */
const checkForNewGameData = (lastCheckedTimestamp = null) => {
  try {
    const recentBattle = getMostRecentBattleDate();
    if (!recentBattle) return { hasNewData: false, newFiles: [] };

    const battlePath = path.join(RAW_DATA_PATH, 'game_records', recentBattle);
    if (!fs.existsSync(battlePath)) return { hasNewData: false, newFiles: [] };

    const files = fs.readdirSync(battlePath);
    const newFiles = [];

    for (const file of files) {
      const filePath = path.join(battlePath, file);
      const stats = fs.statSync(filePath);
      
      // Check if file was modified after last check
      if (!lastCheckedTimestamp || stats.mtime.getTime() > lastCheckedTimestamp) {
        newFiles.push({
          name: file,
          path: filePath,
          modified: stats.mtime,
          size: stats.size
        });
      }
    }

    return {
      hasNewData: newFiles.length > 0,
      newFiles,
      battleDate: recentBattle,
      totalFiles: files.length
    };
  } catch (error) {
    console.error('Error checking for new game data:', error);
    return { hasNewData: false, newFiles: [], error: error.message };
  }
};

/**
 * Parse PGN file for basic game information
 */
const parsePGNFile = (filePath) => {
  try {
    if (!fs.existsSync(filePath) || !filePath.endsWith('.pgn')) {
      return null;
    }

    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    
    const gameInfo = {
      fileName: path.basename(filePath),
      filePath: filePath
    };

    // Extract header information
    for (const line of lines) {
      if (line.startsWith('[Event ')) gameInfo.event = line.match(/\[Event "(.+)"\]/)?.[1];
      if (line.startsWith('[White ')) gameInfo.white = line.match(/\[White "(.+)"\]/)?.[1];
      if (line.startsWith('[Black ')) gameInfo.black = line.match(/\[Black "(.+)"\]/)?.[1];
      if (line.startsWith('[Result ')) gameInfo.result = line.match(/\[Result "(.+)"\]/)?.[1];
      if (line.startsWith('[Date ')) gameInfo.date = line.match(/\[Date "(.+)"\]/)?.[1];
      if (line.startsWith('[TimeControl ')) gameInfo.timeControl = line.match(/\[TimeControl "(.+)"\]/)?.[1];
    }

    // Extract move count (basic)
    const moveLines = lines.filter(line => !line.startsWith('[') && line.trim() !== '');
    const allMoves = moveLines.join(' ').replace(/\d+\./g, '').split(/\s+/).filter(m => m && !m.includes('*'));
    gameInfo.moveCount = allMoves.length;
    gameInfo.isComplete = content.includes('1-0') || content.includes('0-1') || content.includes('1/2-1/2');

    return gameInfo;
  } catch (error) {
    console.error('Error parsing PGN file:', error);
    return null;
  }
};

/**
 * Get current live games (incomplete PGN files)
 */
const getCurrentLiveGames = () => {
  try {
    const recentBattle = getMostRecentBattleDate();
    if (!recentBattle) return [];

    const battlePath = path.join(RAW_DATA_PATH, 'game_records', recentBattle);
    if (!fs.existsSync(battlePath)) return [];

    const files = fs.readdirSync(battlePath).filter(f => f.endsWith('.pgn'));
    const liveGames = [];

    for (const file of files) {
      const filePath = path.join(battlePath, file);
      const gameInfo = parsePGNFile(filePath);
      
      if (gameInfo && !gameInfo.isComplete) {
        liveGames.push({
          ...gameInfo,
          lastModified: fs.statSync(filePath).mtime
        });
      }
    }

    return liveGames.sort((a, b) => b.lastModified - a.lastModified);
  } catch (error) {
    console.error('Error getting live games:', error);
    return [];
  }
};

/**
 * Get game statistics from recent battles
 */
const getRecentGameStats = (daysBack = 7) => {
  try {
    const availableDates = getAvailableBattleDates();
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysBack);

    const recentStats = {
      totalGames: 0,
      completedGames: 0,
      liveGames: 0,
      engines: new Set(),
      battleDates: []
    };

    for (const battleDate of availableDates.reverse()) {
      // Extract date from folder name "Engine Battle 20250925"
      const dateMatch = battleDate.match(/(\d{8})$/);
      if (!dateMatch) continue;

      const battleDateObj = new Date(
        dateMatch[1].substring(0, 4),
        parseInt(dateMatch[1].substring(4, 6)) - 1,
        dateMatch[1].substring(6, 8)
      );

      if (battleDateObj < cutoffDate) break;

      const battlePath = path.join(RAW_DATA_PATH, 'game_records', battleDate);
      if (!fs.existsSync(battlePath)) continue;

      const files = fs.readdirSync(battlePath).filter(f => f.endsWith('.pgn'));
      let completedCount = 0;
      let liveCount = 0;

      for (const file of files) {
        const filePath = path.join(battlePath, file);
        const gameInfo = parsePGNFile(filePath);
        
        if (gameInfo) {
          recentStats.totalGames++;
          if (gameInfo.white) recentStats.engines.add(gameInfo.white);
          if (gameInfo.black) recentStats.engines.add(gameInfo.black);
          
          if (gameInfo.isComplete) {
            completedCount++;
          } else {
            liveCount++;
          }
        }
      }

      recentStats.completedGames += completedCount;
      recentStats.liveGames += liveCount;
      recentStats.battleDates.push({
        date: battleDate,
        totalGames: files.length,
        completedGames: completedCount,
        liveGames: liveCount
      });
    }

    return {
      ...recentStats,
      engines: Array.from(recentStats.engines),
      lastUpdated: new Date().toISOString()
    };
  } catch (error) {
    console.error('Error getting recent game stats:', error);
    return null;
  }
};

module.exports = {
  getAvailableBattleDates,
  getMostRecentBattleDate,
  checkForNewGameData,
  parsePGNFile,
  getCurrentLiveGames,
  getRecentGameStats
};