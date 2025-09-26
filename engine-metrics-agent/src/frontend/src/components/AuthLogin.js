import React, { useState } from 'react';

function AuthLogin({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Simple password authentication for now
    // In production, this would use proper authentication
    if (password === 'v7p3r-analytics-2025') {
      onLogin(true);
      setError('');
    } else {
      setError('Invalid password. Access denied.');
      setPassword('');
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '10px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        maxWidth: '400px',
        width: '100%'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#333', marginBottom: '10px' }}>🏆 V7P3R Analytics</h1>
          <p style={{ color: '#666', fontSize: '14px' }}>Chess Engine Metrics Agent</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '8px', 
              color: '#333',
              fontWeight: 'bold'
            }}>
              🔐 Access Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter access password"
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #ddd',
                borderRadius: '5px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              autoFocus
            />
          </div>

          {error && (
            <div style={{
              backgroundColor: '#f44336',
              color: 'white',
              padding: '10px',
              borderRadius: '5px',
              marginBottom: '20px',
              fontSize: '14px'
            }}>
              ❌ {error}
            </div>
          )}

          <button
            type="submit"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#4caf50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'background-color 0.3s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#45a049'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#4caf50'}
          >
            🚀 Access Analytics Platform
          </button>
        </form>

        <div style={{ 
          marginTop: '30px', 
          padding: '15px', 
          backgroundColor: '#f9f9f9', 
          borderRadius: '5px',
          fontSize: '12px',
          color: '#666'
        }}>
          <div><strong>🔒 Secure Access:</strong> This platform processes cost-generating AI queries</div>
          <div style={{ marginTop: '5px' }}><strong>📊 Data:</strong> V7P3R tournament results and performance metrics</div>
          <div style={{ marginTop: '5px' }}><strong>🤖 AI:</strong> Custom chess engine analysis powered by advanced language models</div>
        </div>
      </div>
    </div>
  );
}

export default AuthLogin;