import React, { useState } from 'react';
import './App.css';
import AuthLogin from './components/AuthLogin';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import HealthCheck from './components/HealthCheck';
import LiveGameMonitor from './components/LiveGameMonitor';

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
    <nav>
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={() => setCurrentPage('dashboard')}
          className={currentPage === 'dashboard' ? 'nav-active' : ''}
        >
          🏆 Dashboard
        </button>
        <button
          onClick={() => setCurrentPage('live')}
          className={currentPage === 'live' ? 'nav-active' : ''}
        >
          � Live Monitor
        </button>
        <button
          onClick={() => setCurrentPage('health')}
          className={currentPage === 'health' ? 'nav-active' : ''}
        >
          🏥 Health Check
        </button>
      </div>
      
      <button
        onClick={handleLogout}
        style={{
          backgroundColor: '#f85149',
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '14px'
        }}
      >
        🔒 Logout
      </button>
    </nav>
  );

  return (
    <div className="App">
      <Navigation />
      
      {currentPage === 'dashboard' && <AnalyticsDashboard />}
      {currentPage === 'live' && <LiveGameMonitor />}
      {currentPage === 'health' && <HealthCheck />}
    </div>
  );
}

export default App;