import React, { useState } from 'react';
import './App.css';
import AuthLogin from './components/AuthLogin';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import HealthCheck from './components/HealthCheck';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');

  const handleLogin = (success) => {
    setIsAuthenticated(success);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setCurrentPage('dashboard');
  };

  // If not authenticated, show login page
  if (!isAuthenticated) {
    return <AuthLogin onLogin={handleLogin} />;
  }

  // Navigation component
  const Navigation = () => (
    <div style={{
      backgroundColor: '#333',
      padding: '10px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      color: 'white'
    }}>
      <div style={{ display: 'flex', gap: '20px' }}>
        <button
          onClick={() => setCurrentPage('dashboard')}
          style={{
            backgroundColor: currentPage === 'dashboard' ? '#4caf50' : 'transparent',
            color: 'white',
            border: '1px solid #555',
            padding: '8px 16px',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          🏆 Dashboard
        </button>
        <button
          onClick={() => setCurrentPage('health')}
          style={{
            backgroundColor: currentPage === 'health' ? '#4caf50' : 'transparent',
            color: 'white',
            border: '1px solid #555',
            padding: '8px 16px',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          🏥 Health Check
        </button>
      </div>
      
      <button
        onClick={handleLogout}
        style={{
          backgroundColor: '#f44336',
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '5px',
          cursor: 'pointer'
        }}
      >
        🔒 Logout
      </button>
    </div>
  );

  return (
    <div className="App">
      <Navigation />
      
      {currentPage === 'dashboard' && <AnalyticsDashboard />}
      {currentPage === 'health' && <HealthCheck />}
    </div>
  );
}

export default App;