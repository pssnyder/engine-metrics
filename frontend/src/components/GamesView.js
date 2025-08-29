import React, { useState, useEffect } from 'react';
import apiService from '../apiService';

const GamesView = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    limit: 50,
    white_player: '',
    black_player: '',
    result: '',
    termination: '',
    is_decisive_win: null,
    is_soft_loss: null,
    is_missed_win: null
  });

  const fetchGames = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Filter out empty values
      const activeFilters = Object.entries(filters).reduce((acc, [key, value]) => {
        if (value !== '' && value !== null) {
          acc[key] = value;
        }
        return acc;
      }, {});

      const response = await apiService.searchGames(activeFilters);
      setGames(response.data.games);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch games');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGames();
  }, []);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSearch = () => {
    fetchGames();
  };

  const clearFilters = () => {
    setFilters({
      limit: 50,
      white_player: '',
      black_player: '',
      result: '',
      termination: '',
      is_decisive_win: null,
      is_soft_loss: null,
      is_missed_win: null
    });
  };

  const formatResult = (result, whitePlayer, blackPlayer) => {
    if (result === '1-0') return 'White wins';
    if (result === '0-1') return 'Black wins';
    if (result === '1/2-1/2') return 'Draw';
    return result;
  };

  const getResultClass = (result) => {
    if (result === '1-0') return 'result-win';
    if (result === '0-1') return 'result-win';
    if (result === '1/2-1/2') return 'result-draw';
    return '';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    try {
      // Handle various date formats
      if (dateStr.includes('T')) {
        return new Date(dateStr).toLocaleDateString();
      } else if (dateStr.includes('.')) {
        const [year, month, day] = dateStr.split('.');
        return `${month}/${day}/${year}`;
      } else {
        return dateStr;
      }
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return <div className="loading">Loading games...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error Loading Games</h3>
        <p>{error}</p>
        <button onClick={fetchGames} className="refresh-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="games-view">
      <h2>Game History</h2>
      
      {/* Filters */}
      <div className="metric-card" style={{ marginBottom: '20px' }}>
        <h3>Filter Games</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', marginBottom: '15px' }}>
          <div>
            <label>White Player:</label>
            <input
              type="text"
              value={filters.white_player}
              onChange={(e) => handleFilterChange('white_player', e.target.value)}
              placeholder="e.g., v7p3r"
              style={{ width: '100%', padding: '5px', marginTop: '5px' }}
            />
          </div>
          
          <div>
            <label>Black Player:</label>
            <input
              type="text"
              value={filters.black_player}
              onChange={(e) => handleFilterChange('black_player', e.target.value)}
              placeholder="e.g., slowmate"
              style={{ width: '100%', padding: '5px', marginTop: '5px' }}
            />
          </div>
          
          <div>
            <label>Result:</label>
            <select
              value={filters.result}
              onChange={(e) => handleFilterChange('result', e.target.value)}
              style={{ width: '100%', padding: '5px', marginTop: '5px' }}
            >
              <option value="">All Results</option>
              <option value="1-0">White Wins</option>
              <option value="0-1">Black Wins</option>
              <option value="1/2-1/2">Draws</option>
            </select>
          </div>
          
          <div>
            <label>Termination:</label>
            <input
              type="text"
              value={filters.termination}
              onChange={(e) => handleFilterChange('termination', e.target.value)}
              placeholder="e.g., mate, resign"
              style={{ width: '100%', padding: '5px', marginTop: '5px' }}
            />
          </div>
          
          <div>
            <label>Limit:</label>
            <select
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
              style={{ width: '100%', padding: '5px', marginTop: '5px' }}
            >
              <option value={25}>25 games</option>
              <option value={50}>50 games</option>
              <option value={100}>100 games</option>
              <option value={200}>200 games</option>
            </select>
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '15px' }}>
          <div>
            <label>
              <input
                type="checkbox"
                checked={filters.is_decisive_win === true}
                onChange={(e) => handleFilterChange('is_decisive_win', e.target.checked ? true : null)}
              />
              {' '}Decisive Wins Only
            </label>
          </div>
          
          <div>
            <label>
              <input
                type="checkbox"
                checked={filters.is_soft_loss === true}
                onChange={(e) => handleFilterChange('is_soft_loss', e.target.checked ? true : null)}
              />
              {' '}Soft Losses Only
            </label>
          </div>
          
          <div>
            <label>
              <input
                type="checkbox"
                checked={filters.is_missed_win === true}
                onChange={(e) => handleFilterChange('is_missed_win', e.target.checked ? true : null)}
              />
              {' '}Missed Wins Only
            </label>
          </div>
        </div>
        
        <div>
          <button onClick={handleSearch} className="refresh-button" style={{ marginRight: '10px' }}>
            Search
          </button>
          <button onClick={clearFilters} className="refresh-button" style={{ background: '#6c757d' }}>
            Clear Filters
          </button>
        </div>
      </div>

      {/* Results Summary */}
      <div style={{ marginBottom: '20px', padding: '10px', background: '#f8f9fa', borderRadius: '4px' }}>
        <strong>Found {games.length} games</strong>
      </div>

      {/* Games Table */}
      {games.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="games-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>White</th>
                <th>Black</th>
                <th>Result</th>
                <th>Termination</th>
                <th>Moves</th>
                <th>Classifications</th>
                <th>Avg Time</th>
                <th>Avg Depth</th>
              </tr>
            </thead>
            <tbody>
              {games.map((game) => (
                <tr key={game.id}>
                  <td>{formatDate(game.date)}</td>
                  <td style={{ fontSize: '0.9rem' }}>
                    {game.white_player}
                  </td>
                  <td style={{ fontSize: '0.9rem' }}>
                    {game.black_player}
                  </td>
                  <td className={getResultClass(game.result)}>
                    {formatResult(game.result, game.white_player, game.black_player)}
                  </td>
                  <td style={{ fontSize: '0.9rem' }}>
                    {game.termination || 'Unknown'}
                  </td>
                  <td>{game.total_moves || 'N/A'}</td>
                  <td>
                    {game.is_decisive_win && (
                      <span className="classification-tag tag-decisive">Decisive</span>
                    )}
                    {game.is_soft_loss && (
                      <span className="classification-tag tag-soft-loss">Soft Loss</span>
                    )}
                    {game.is_missed_win && (
                      <span className="classification-tag tag-missed-win">Missed Win</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.9rem' }}>
                    {game.white_avg_time && game.black_avg_time ? (
                      <div>
                        W: {game.white_avg_time.toFixed(1)}s<br/>
                        B: {game.black_avg_time.toFixed(1)}s
                      </div>
                    ) : 'N/A'}
                  </td>
                  <td style={{ fontSize: '0.9rem' }}>
                    {game.white_avg_depth && game.black_avg_depth ? (
                      <div>
                        W: {game.white_avg_depth.toFixed(1)}<br/>
                        B: {game.black_avg_depth.toFixed(1)}
                      </div>
                    ) : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          No games found matching the current filters.
        </div>
      )}
    </div>
  );
};

export default GamesView;
