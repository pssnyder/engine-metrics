import React, { useState, useEffect } from 'react';
import useAutoRefresh from '../hooks/useAutoRefresh';

function LiveGameMonitor() {
  const {
    liveGames,
    recentStats,
    hasNewData,
    isRefreshing,
    lastUpdateTime,
    refreshCount,
    manualRefresh,
    clearNewDataFlag,
    pauseAutoRefresh
  } = useAutoRefresh(15000); // Check every 15 seconds for live games

  const [selectedGame, setSelectedGame] = useState(null);
  const [showAllStats, setShowAllStats] = useState(false);

  // Auto-select the most recently updated game
  useEffect(() => {
    if (liveGames.length > 0 && !selectedGame) {
      setSelectedGame(liveGames[0]);
    }
  }, [liveGames, selectedGame]);

  const formatTimeAgo = (date) => {
    if (!date) return 'Unknown';
    const now = new Date();
    const gameDate = new Date(date);
    const diffMs = now - gameDate;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ${diffMins % 60}m ago`;
    return gameDate.toLocaleDateString();
  };

  const getGameStatus = (game) => {
    if (!game) return 'No Game';
    if (game.isComplete) return 'Completed';
    
    const lastUpdate = new Date(game.lastModified);
    const now = new Date();
    const timeSinceUpdate = (now - lastUpdate) / 60000; // minutes
    
    if (timeSinceUpdate < 2) return 'Live - Active';
    if (timeSinceUpdate < 10) return 'Live - Recent';
    return 'Live - Paused';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Live - Active': return '#2ea043';
      case 'Live - Recent': return '#ffa657';
      case 'Live - Paused': return '#7d8590';
      case 'Completed': return '#58a6ff';
      default: return '#e6e6e6';
    }
  };

  return (
    <div className="live-monitor-container">
      {/* Header with Status */}
      <div className="monitor-header">
        <div className="header-left">
          <h2 style={{ color: '#58a6ff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            🎮 Live Game Monitor
            {hasNewData && (
              <span 
                className="new-data-indicator"
                onClick={clearNewDataFlag}
                title="New game data available - click to dismiss"
              >
                🔄
              </span>
            )}
          </h2>
          <p style={{ color: '#c9d1d9', fontSize: '14px', margin: '4px 0 0 0' }}>
            {liveGames.length} active games • Updated {formatTimeAgo(lastUpdateTime)} • Refresh #{refreshCount}
          </p>
        </div>
        
        <div className="header-controls">
          <button 
            onClick={manualRefresh} 
            disabled={isRefreshing}
            className="refresh-button"
          >
            {isRefreshing ? '🔄 Refreshing...' : '🔄 Refresh'}
          </button>
          <button 
            onClick={() => setShowAllStats(!showAllStats)}
            className="toggle-stats-button"
          >
            {showAllStats ? '📊 Hide Stats' : '📊 Show Stats'}
          </button>
        </div>
      </div>

      <div className="monitor-content">
        {/* Live Games List */}
        <div className="games-panel">
          <h3 style={{ color: '#7ee787', margin: '0 0 1rem 0' }}>Active Games</h3>
          
          {liveGames.length === 0 ? (
            <div className="no-games">
              <p style={{ color: '#7d8590', fontStyle: 'italic' }}>
                No live games currently active
              </p>
            </div>
          ) : (
            <div className="games-list">
              {liveGames.map((game, index) => {
                const status = getGameStatus(game);
                const isSelected = selectedGame && selectedGame.fileName === game.fileName;
                
                return (
                  <div 
                    key={game.fileName} 
                    className={`game-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedGame(game);
                      pauseAutoRefresh(); // Pause auto-refresh when user selects a game
                    }}
                  >
                    <div className="game-header">
                      <div className="game-players">
                        <strong>{game.white || 'White'}</strong> vs <strong>{game.black || 'Black'}</strong>
                      </div>
                      <div 
                        className="game-status"
                        style={{ color: getStatusColor(status) }}
                      >
                        {status}
                      </div>
                    </div>
                    
                    <div className="game-details">
                      <span>Moves: {game.moveCount || 0}</span>
                      <span>Updated: {formatTimeAgo(game.lastModified)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Game Details Panel */}
        <div className="game-details-panel">
          {selectedGame ? (
            <div>
              <h3 style={{ color: '#58a6ff', margin: '0 0 1rem 0' }}>
                Game Details
              </h3>
              
              <div className="selected-game-info">
                <div className="game-matchup">
                  <div className="player-info">
                    <div className="player-name white-player">⚪ {selectedGame.white || 'White'}</div>
                    <div className="vs-separator">vs</div>
                    <div className="player-name black-player">⚫ {selectedGame.black || 'Black'}</div>
                  </div>
                </div>

                <div className="game-meta">
                  <div className="meta-item">
                    <label>File:</label>
                    <span>{selectedGame.fileName}</span>
                  </div>
                  <div className="meta-item">
                    <label>Status:</label>
                    <span style={{ color: getStatusColor(getGameStatus(selectedGame)) }}>
                      {getGameStatus(selectedGame)}
                    </span>
                  </div>
                  <div className="meta-item">
                    <label>Moves:</label>
                    <span>{selectedGame.moveCount || 0}</span>
                  </div>
                  <div className="meta-item">
                    <label>Last Update:</label>
                    <span>{formatTimeAgo(selectedGame.lastModified)}</span>
                  </div>
                  {selectedGame.timeControl && (
                    <div className="meta-item">
                      <label>Time Control:</label>
                      <span>{selectedGame.timeControl}</span>
                    </div>
                  )}
                  {selectedGame.event && (
                    <div className="meta-item">
                      <label>Event:</label>
                      <span>{selectedGame.event}</span>
                    </div>
                  )}
                </div>

                <div className="game-actions">
                  <button 
                    onClick={() => window.open(`file://${selectedGame.filePath}`, '_blank')}
                    className="view-pgn-button"
                    title="Open PGN file in default editor"
                  >
                    📄 View PGN
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <p style={{ color: '#7d8590', fontStyle: 'italic', textAlign: 'center' }}>
                Select a game to view details
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Stats Panel (Collapsible) */}
      {showAllStats && recentStats && (
        <div className="recent-stats-panel">
          <h3 style={{ color: '#ffa657', margin: '0 0 1rem 0' }}>📈 Recent Activity (7 days)</h3>
          
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{recentStats.totalGames}</div>
              <div className="stat-label">Total Games</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{recentStats.completedGames}</div>
              <div className="stat-label">Completed</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{recentStats.liveGames}</div>
              <div className="stat-label">Live Games</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{recentStats.engines?.length || 0}</div>
              <div className="stat-label">Active Engines</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{recentStats.battleDates?.length || 0}</div>
              <div className="stat-label">Battle Days</div>
            </div>
          </div>
          
          {recentStats.engines && (
            <div className="engines-list">
              <h4 style={{ color: '#c9d1d9', margin: '1rem 0 0.5rem 0' }}>Active Engines:</h4>
              <div className="engines-tags">
                {recentStats.engines.map(engine => (
                  <span key={engine} className="engine-tag">{engine}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default LiveGameMonitor;