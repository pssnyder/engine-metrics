import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import GamesView from './components/GamesView';
import SettingsView from './components/SettingsView';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'games':
        return <GamesView />;
      case 'settings':
        return <SettingsView />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="App">
      <header className="header">
        <div className="container">
          <h1>Engine Metrics Dashboard</h1>
          <p>V7P3R vs SlowMate Performance Analysis</p>
        </div>
      </header>

      <div className="container">
        {/* Navigation Tabs */}
        <div className="nav-tabs" style={{ 
          display: 'flex', 
          marginBottom: '20px', 
          borderBottom: '2px solid #eee',
          gap: '0'
        }}>
          {[
            { id: 'dashboard', label: 'Dashboard', icon: '📊' },
            { id: 'games', label: 'Game History', icon: '♟' },
            { id: 'settings', label: 'Settings', icon: '⚙️' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              style={{
                padding: '12px 24px',
                border: 'none',
                background: activeTab === tab.id ? '#667eea' : 'transparent',
                color: activeTab === tab.id ? 'white' : '#666',
                cursor: 'pointer',
                borderBottom: activeTab === tab.id ? '3px solid #764ba2' : '3px solid transparent',
                transition: 'all 0.2s ease',
                fontSize: '16px',
                fontWeight: activeTab === tab.id ? 'bold' : 'normal'
              }}
              onMouseOver={(e) => {
                if (activeTab !== tab.id) {
                  e.target.style.background = '#f8f9fa';
                  e.target.style.color = '#333';
                }
              }}
              onMouseOut={(e) => {
                if (activeTab !== tab.id) {
                  e.target.style.background = 'transparent';
                  e.target.style.color = '#666';
                }
              }}
            >
              <span style={{ marginRight: '8px' }}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Active Component */}
        <main>
          {renderActiveComponent()}
        </main>
      </div>

      <footer style={{ 
        textAlign: 'center', 
        padding: '20px', 
        color: '#666', 
        marginTop: '40px',
        borderTop: '1px solid #eee'
      }}>
        <p>Engine Metrics Dashboard | Monitoring V7P3R vs SlowMate Development Battle</p>
      </footer>
    </div>
  );
}

export default App;
