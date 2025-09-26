const admin = require('firebase-admin');
const functions = require('firebase-functions');

/**
 * Get V7P3R overall metrics
 */
const getOverallMetrics = async () => {
  try {
    // In a real implementation, this would query Firestore for actual data
    // For now, returning mock data structure
    
    return {
      totalGames: 2547,
      totalWins: 1423,
      totalLosses: 892,
      totalTies: 232,
      winRate: 55.8,
      bestVersion: 'V7P3R_v12.0',
      worstVersion: 'V7P3R_v10.1',
      availableVersions: [
        'V7P3R_v12.0', 'V7P3R_v11.0', 'V7P3R_v10.8', 
        'V7P3R_v10.2', 'V7P3R_v10.0', 'V7P3R_v9.3', 'V7P3R_v7.0'
      ]
    };
  } catch (error) {
    console.error('Error fetching overall metrics:', error);
    throw error;
  }
};

/**
 * Get version-specific metrics
 */
const getVersionMetrics = async (version) => {
  try {
    // Mock data for different versions
    const versionData = {
      'V7P3R_v12.0': { 
        games: 234, wins: 156, losses: 52, ties: 26, 
        checkmates: 67, timeouts: 12, resignations: 23, adjudications: 5
      },
      'V7P3R_v11.0': { 
        games: 387, wins: 234, losses: 112, ties: 41, 
        checkmates: 89, timeouts: 23, resignations: 45, adjudications: 8
      },
      'V7P3R_v10.8': { 
        games: 456, wins: 278, losses: 134, ties: 44, 
        checkmates: 102, timeouts: 28, resignations: 67, adjudications: 12
      },
      'V7P3R_v10.2': { 
        games: 298, wins: 145, losses: 123, ties: 30, 
        checkmates: 56, timeouts: 34, resignations: 89, adjudications: 15
      },
      'V7P3R_v10.0': { 
        games: 345, wins: 167, losses: 134, ties: 44, 
        checkmates: 72, timeouts: 45, resignations: 67, adjudications: 18
      },
      'V7P3R_v9.3': { 
        games: 423, wins: 189, losses: 178, ties: 56, 
        checkmates: 78, timeouts: 67, resignations: 123, adjudications: 23
      },
      'V7P3R_v7.0': { 
        games: 404, wins: 254, losses: 112, ties: 38, 
        checkmates: 98, timeouts: 34, resignations: 45, adjudications: 12
      }
    };

    if (version === 'All') {
      // Aggregate all versions
      const totals = {
        games: 0, wins: 0, losses: 0, ties: 0,
        checkmates: 0, timeouts: 0, resignations: 0, adjudications: 0
      };

      Object.values(versionData).forEach(data => {
        Object.keys(totals).forEach(key => {
          totals[key] += data[key];
        });
      });

      const winRate = ((totals.wins / totals.games) * 100).toFixed(1);
      
      return {
        version: 'All Versions',
        ...totals,
        winRate: parseFloat(winRate)
      };
    }

    const data = versionData[version];
    if (!data) {
      return {
        version,
        games: 0, wins: 0, losses: 0, ties: 0,
        checkmates: 0, timeouts: 0, resignations: 0, adjudications: 0,
        winRate: 0
      };
    }

    const winRate = ((data.wins / data.games) * 100).toFixed(1);
    
    return {
      version,
      ...data,
      winRate: parseFloat(winRate)
    };
    
  } catch (error) {
    console.error('Error fetching version metrics:', error);
    throw error;
  }
};

/**
 * Process AI chat queries about V7P3R performance
 */
const processAnalyticsQuery = async (query) => {
  try {
    // This would integrate with the AI service
    // For now, return a mock response based on query content
    
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('v12.0') && lowerQuery.includes('v11.0')) {
      return {
        answer: `V7P3R v12.0 vs v11.0 Comparison:
        
📊 Performance Summary:
• V12.0: 234 games, 66.7% win rate (156 wins)
• V11.0: 387 games, 60.5% win rate (234 wins)

🎯 Key Improvements in v12.0:
• Higher win rate (+6.2 percentage points)
• Better checkmate efficiency (28.6% vs 23.0%)
• Reduced timeouts (5.1% vs 5.9%)

📈 Trend Analysis:
V12.0 shows significant improvement in tactical play, with fewer timeouts and more decisive victories. The enhanced evaluation system appears to be working effectively.`,
        
        confidence: 0.85,
        sources: ['Tournament Results', 'Version Comparison Analysis'],
        timestamp: new Date().toISOString()
      };
    }
    
    if (lowerQuery.includes('checkmate') || lowerQuery.includes('mate')) {
      return {
        answer: `V7P3R Checkmate Analysis Across Versions:

🏆 Best Performing Versions (Checkmate Rate):
1. V7P3R_v7.0: 24.3% (98/404 games)
2. V7P3R_v12.0: 28.6% (67/234 games)  
3. V7P3R_v10.8: 22.4% (102/456 games)

📊 Overall Stats:
• Total checkmates delivered: 562
• Average checkmate rate: 22.1%
• Most improved: v12.0 (+4.3% vs average)

🎯 Insights:
V12.0 shows the highest checkmate efficiency despite fewer games, indicating improved tactical awareness. V7.0 remains strong with high absolute checkmate count.`,
        
        confidence: 0.92,
        sources: ['Game Termination Analysis', 'Version Performance Data'],
        timestamp: new Date().toISOString()
      };
    }
    
    // Default response
    return {
      answer: `I can help analyze V7P3R performance data. Based on your query "${query}", here are some relevant insights:

📊 Current Data Available:
• 2,547 total games across 7 engine versions
• Win rate: 55.8% overall
• Best performing version: V7P3R_v12.0 (66.7% win rate)

🤖 What I can analyze:
• Version comparisons and performance trends
• Checkmate patterns and tactical improvements  
• Timeout analysis and time management
• Win/loss/tie breakdowns by opponent type
• Engine evolution over development cycles

Try asking more specific questions like:
• "Compare v12.0 vs v10.8 performance"
• "Show timeout patterns across versions"
• "Which version performs best against Stockfish?"`,
      
      confidence: 0.70,
      sources: ['Overall Performance Database'],
      timestamp: new Date().toISOString()
    };
    
  } catch (error) {
    console.error('Error processing analytics query:', error);
    throw error;
  }
};

module.exports = {
  getOverallMetrics,
  getVersionMetrics,
  processAnalyticsQuery
};