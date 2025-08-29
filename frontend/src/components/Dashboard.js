import React, { useState, useEffect } from 'react';
import apiService from '../apiService';

const Dashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (forceRefresh = false) => {
    try {
      setError(null);
      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [metricsResponse, statusResponse] = await Promise.all([
        apiService.getMetricsSummary(forceRefresh),
        apiService.getStatus()
      ]);

      setMetrics(metricsResponse.data);
      setStatus(statusResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Set up periodic refresh every 5 minutes
    const interval = setInterval(() => {
      fetchData();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchData(true);
  };

  const formatLastUpdate = (timestamp) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (loading) {
    return <div className="loading">Loading dashboard data...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error Loading Data</h3>
        <p>{error}</p>
        <button onClick={() => fetchData()} className="refresh-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2>Engine Battle Dashboard</h2>
            <p>V7P3R vs SlowMate Performance Metrics</p>
          </div>
          <div>
            <button 
              onClick={handleRefresh} 
              disabled={refreshing}
              className="refresh-button"
            >
              {refreshing ? 'Refreshing...' : 'Force Refresh'}
            </button>
          </div>
        </div>
        
        {status && (
          <div className="status-bar" style={{ marginBottom: '20px', padding: '10px', background: '#f8f9fa', borderRadius: '4px' }}>
            <span className={`status-indicator ${status.processing_status?.is_running ? 'status-healthy' : 'status-warning'}`}></span>
            <strong>Status:</strong> {status.processing_status?.is_running ? 'Running' : 'Stopped'} | 
            <strong> Last Update:</strong> {formatLastUpdate(status.last_update)} | 
            <strong> Total Games:</strong> {status.total_games}
            {status.processing_status?.next_batch_in_minutes !== undefined && (
              <> | <strong>Next Batch:</strong> {status.processing_status.next_batch_in_minutes.toFixed(1)} min</>
            )}
          </div>
        )}
      </div>

      {metrics && (
        <div className="dashboard-grid">
          {/* Overall Statistics */}
          <div className="metric-card">
            <h3>Overall Statistics</h3>
            <div className="metric-value">{metrics.total_games}</div>
            <div className="metric-label">Total Head-to-Head Games</div>
            
            <div style={{ marginTop: '15px' }}>
              <div className="stat-row">
                <span className="stat-label">Last Updated:</span>
                <span className="stat-value">{formatLastUpdate(metrics.last_updated)}</span>
              </div>
            </div>
          </div>

          {/* Engine Comparison */}
          <div className="metric-card" style={{ gridColumn: 'span 2' }}>
            <h3>Engine Performance Comparison</h3>
            <div className="engine-comparison">
              {Object.entries(metrics.engines || {}).map(([engineName, engineStats]) => (
                <div key={engineName} className={`engine-stats ${engineName}`}>
                  <div className="engine-name">{engineName}</div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Games Played:</span>
                    <span className="stat-value">{engineStats.total_games}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Win Rate:</span>
                    <span className="stat-value result-win">{formatPercentage(engineStats.win_rate)}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Wins:</span>
                    <span className="stat-value result-win">{engineStats.wins}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Losses:</span>
                    <span className="stat-value result-loss">{engineStats.losses}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Draws:</span>
                    <span className="stat-value result-draw">{engineStats.draws}</span>
                  </div>

                  <hr style={{ margin: '10px 0', border: '1px solid #eee' }} />

                  <div className="stat-row">
                    <span className="stat-label">Decisive Wins:</span>
                    <span className="stat-value">{engineStats.decisive_wins}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Soft Losses:</span>
                    <span className="stat-value">{engineStats.soft_losses}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Missed Wins:</span>
                    <span className="stat-value">{engineStats.missed_wins}</span>
                  </div>

                  {engineStats.average_time_per_move && (
                    <>
                      <hr style={{ margin: '10px 0', border: '1px solid #eee' }} />
                      <div className="stat-row">
                        <span className="stat-label">Avg Time/Move:</span>
                        <span className="stat-value">{engineStats.average_time_per_move.toFixed(2)}s</span>
                      </div>
                    </>
                  )}

                  {engineStats.average_depth && (
                    <div className="stat-row">
                      <span className="stat-label">Avg Depth:</span>
                      <span className="stat-value">{engineStats.average_depth.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Head-to-Head Breakdown */}
          {metrics.head_to_head && Object.keys(metrics.head_to_head).length > 0 && (
            <div className="metric-card">
              <h3>Head-to-Head Breakdown</h3>
              {Object.entries(metrics.head_to_head).map(([matchup, stats]) => (
                <div key={matchup}>
                  <div className="metric-label" style={{ fontWeight: 'bold', marginBottom: '10px' }}>
                    {matchup.replace('_vs_', ' vs ').toUpperCase()}
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Total Games:</span>
                    <span className="stat-value">{stats.total_games}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">White Wins:</span>
                    <span className="stat-value result-win">{stats.white_wins}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Black Wins:</span>
                    <span className="stat-value result-win">{stats.black_wins}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Draws:</span>
                    <span className="stat-value result-draw">{stats.draws}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Decisive Outcomes:</span>
                    <span className="stat-value">{stats.decisive_outcomes}</span>
                  </div>
                  
                  <div className="stat-row">
                    <span className="stat-label">Missed Wins:</span>
                    <span className="stat-value">{stats.missed_wins}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Termination Analysis */}
          {metrics.termination_analysis && (
            <div className="metric-card">
              <h3>Game Terminations</h3>
              {Object.entries(metrics.termination_analysis)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 8)
                .map(([termination, count]) => (
                <div key={termination} className="stat-row">
                  <span className="stat-label">{termination || 'Unknown'}:</span>
                  <span className="stat-value">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
