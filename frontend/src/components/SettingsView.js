import React, { useState, useEffect } from 'react';
import apiService from '../apiService';

const SettingsView = () => {
  const [settings, setSettings] = useState(null);
  const [directories, setDirectories] = useState(null);
  const [engines, setEngines] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [settingsResponse, directoriesResponse, enginesResponse, statusResponse] = await Promise.all([
        apiService.getSettings(),
        apiService.getMonitoredDirectories(),
        apiService.getEngineConfig(),
        apiService.getStatus()
      ]);

      setSettings(settingsResponse.data);
      setDirectories(directoriesResponse.data);
      setEngines(enginesResponse.data);
      setStatus(statusResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatLastUpdate = (timestamp) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  if (loading) {
    return <div className="loading">Loading settings...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error Loading Settings</h3>
        <p>{error}</p>
        <button onClick={fetchData} className="refresh-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="settings-view">
      <h2>System Configuration</h2>

      {/* System Status */}
      {status && (
        <div className="metric-card">
          <h3>System Status</h3>
          <div className="stat-row">
            <span className="stat-label">Processing Status:</span>
            <span className="stat-value">
              <span className={`status-indicator ${status.processing_status?.is_running ? 'status-healthy' : 'status-warning'}`}></span>
              {status.processing_status?.is_running ? 'Running' : 'Stopped'}
            </span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Last Update:</span>
            <span className="stat-value">{formatLastUpdate(status.last_update)}</span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Total Games:</span>
            <span className="stat-value">{status.total_games}</span>
          </div>
          
          {status.processing_status?.monitored_directories && (
            <div className="stat-row">
              <span className="stat-label">Monitored Directories:</span>
              <span className="stat-value">{status.processing_status.monitored_directories.length}</span>
            </div>
          )}
          
          {status.processing_status?.next_batch_in_minutes !== undefined && (
            <div className="stat-row">
              <span className="stat-label">Next Batch Processing:</span>
              <span className="stat-value">{status.processing_status.next_batch_in_minutes.toFixed(1)} minutes</span>
            </div>
          )}
          
          {status.processing_status?.batch_interval_minutes && (
            <div className="stat-row">
              <span className="stat-label">Batch Interval:</span>
              <span className="stat-value">{status.processing_status.batch_interval_minutes} minutes</span>
            </div>
          )}
        </div>
      )}

      {/* Engine Configuration */}
      {engines && (
        <div className="metric-card">
          <h3>Engine Configuration</h3>
          <div className="stat-row">
            <span className="stat-label">Target Engines:</span>
            <span className="stat-value">{engines.target_engines?.join(', ') || 'None configured'}</span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Version Pattern:</span>
            <span className="stat-value" style={{ fontFamily: 'monospace' }}>{engines.version_pattern || 'Not set'}</span>
          </div>
        </div>
      )}

      {/* Processing Settings */}
      {settings && (
        <div className="metric-card">
          <h3>Processing Settings</h3>
          {settings.processing && (
            <>
              <div className="stat-row">
                <span className="stat-label">Batch Interval:</span>
                <span className="stat-value">{settings.processing.batch_interval_minutes} minutes</span>
              </div>
              
              <div className="stat-row">
                <span className="stat-label">Encoding Fallbacks:</span>
                <span className="stat-value">{settings.processing.encoding_fallbacks?.join(', ') || 'None'}</span>
              </div>
            </>
          )}
          
          {settings.metrics && (
            <>
              <div className="stat-row">
                <span className="stat-label">Material Advantage Threshold:</span>
                <span className="stat-value">{settings.metrics.material_advantage_threshold} pawns</span>
              </div>
              
              {settings.metrics.time_control_categories && (
                <div className="stat-row">
                  <span className="stat-label">Time Control Categories:</span>
                  <span className="stat-value">{settings.metrics.time_control_categories.join(', ')}</span>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Monitored Directories */}
      {directories && (
        <div className="metric-card">
          <h3>Monitored Directories</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <strong>File Patterns:</strong> {directories.file_patterns?.join(', ') || 'None'}
          </div>
          
          {directories.monitored_directories && directories.monitored_directories.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="games-table">
                <thead>
                  <tr>
                    <th>Directory Path</th>
                    <th>Absolute Path</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {directories.monitored_directories.map((dir, index) => (
                    <tr key={index}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>{dir.path}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#666' }}>{dir.absolute_path}</td>
                      <td>
                        {dir.exists ? (
                          dir.is_directory ? (
                            <span style={{ color: '#28a745' }}>✓ Valid Directory</span>
                          ) : (
                            <span style={{ color: '#ffc107' }}>⚠ Not a Directory</span>
                          )
                        ) : (
                          <span style={{ color: '#dc3545' }}>✗ Not Found</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
              No directories configured for monitoring.
            </div>
          )}
        </div>
      )}

      {/* Server Configuration */}
      {settings && settings.server && (
        <div className="metric-card">
          <h3>Server Configuration</h3>
          <div className="stat-row">
            <span className="stat-label">Port:</span>
            <span className="stat-value">{settings.server.port}</span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Debug Mode:</span>
            <span className="stat-value">{settings.server.debug ? 'Enabled' : 'Disabled'}</span>
          </div>
        </div>
      )}

      {/* Configuration File Help */}
      <div className="metric-card">
        <h3>Configuration Instructions</h3>
        <div style={{ fontSize: '0.9rem', lineHeight: '1.6', color: '#666' }}>
          <p>
            <strong>To modify settings:</strong> Edit the <code>config/settings.yaml</code> file in your project directory and restart the application.
          </p>
          
          <p>
            <strong>To add network directories:</strong> Add paths to the <code>directories.network_paths</code> section in your configuration file. 
            These can be Windows network shares (e.g., <code>//PC-NAME/shared-folder</code>) or synced local directories.
          </p>
          
          <p>
            <strong>Directory Status:</strong> Green checkmarks indicate directories that are accessible and being monitored. 
            Fix any directories showing warnings or errors in the table above.
          </p>
          
          <p>
            <strong>Processing:</strong> The system automatically processes new PGN files every {settings?.processing?.batch_interval_minutes || 5} minutes. 
            Only games between versioned {engines?.target_engines?.join(' and ') || 'target engines'} are included in the metrics.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;
