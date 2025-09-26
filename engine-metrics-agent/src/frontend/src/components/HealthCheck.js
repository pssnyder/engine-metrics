import React, { useState, useEffect } from 'react';

function HealthCheck() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [aiStatus, setAiStatus] = useState('checking');

  const checkServiceHealth = async (url, serviceName) => {
    try {
      const response = await fetch(url, {
        method: 'GET',
        timeout: 5000
      });
      
      if (response.ok) {
        return 'running';
      } else {
        return 'error';
      }
    } catch (error) {
      console.log(`${serviceName} not available:`, error);
      return 'starting';
    }
  };

  useEffect(() => {
    const checkServices = async () => {
      // Check backend health
      const backendHealth = await checkServiceHealth(
        'http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/health',
        'Backend'
      );
      setBackendStatus(backendHealth);

      // Check AI service health
      const aiHealth = await checkServiceHealth(
        'http://127.0.0.1:5020/',
        'AI Service'
      );
      setAiStatus(aiHealth);
    };

    checkServices();
    
    // Check every 10 seconds
    const interval = setInterval(checkServices, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusDisplay = (status) => {
    switch(status) {
      case 'running':
        return { color: '#4caf50', icon: '✅', text: 'Running' };
      case 'error':
        return { color: '#f44336', icon: '❌', text: 'Error' };
      case 'starting':
        return { color: '#ff9800', icon: '⏳', text: 'Starting...' };
      default:
        return { color: '#757575', icon: '🔍', text: 'Checking...' };
    }
  };

  const frontendStatus = getStatusDisplay('running');
  const backendStatusDisplay = getStatusDisplay(backendStatus);
  const aiStatusDisplay = getStatusDisplay(aiStatus);

  const allServicesRunning = backendStatus === 'running' && aiStatus === 'running';

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>🏥 Engine Metrics Agent - Health Check</h1>
      
      <div style={{ margin: '20px 0' }}>
        <h2>🚀 System Status</h2>
        <div style={{ color: frontendStatus.color, fontSize: '18px', margin: '10px 0' }}>
          {frontendStatus.icon} Frontend: {frontendStatus.text}
        </div>
        <div style={{ color: backendStatusDisplay.color, fontSize: '18px', margin: '10px 0' }}>
          {backendStatusDisplay.icon} Backend: {backendStatusDisplay.text}
        </div>
        <div style={{ color: aiStatusDisplay.color, fontSize: '18px', margin: '10px 0' }}>
          {aiStatusDisplay.icon} AI Service: {aiStatusDisplay.text}
        </div>
        
        {allServicesRunning && (
          <div style={{ margin: '10px 0', padding: '15px', backgroundColor: '#4caf50', color: 'white', borderRadius: '5px' }}>
            🎉 All services are running! Platform is fully operational.
          </div>
        )}
      </div>
      
      <div style={{ margin: '20px 0' }}>
        <h3>🔗 Service URLs</h3>
        <div style={{ textAlign: 'left', maxWidth: '600px' }}>
          <div style={{ margin: '5px 0' }}>🌐 <strong>Frontend:</strong> http://localhost:3010</div>
          <div style={{ margin: '5px 0' }}>⚡ <strong>Backend Functions:</strong> http://127.0.0.1:5010</div>
          <div style={{ margin: '5px 0' }}>🤖 <strong>AI Service:</strong> http://127.0.0.1:5020</div>
          <div style={{ margin: '5px 0' }}>📊 <strong>Firebase Emulator UI:</strong> http://127.0.0.1:4010</div>
        </div>
      </div>

      <div style={{ margin: '20px 0' }}>
        <h3>📊 Platform Features</h3>
        <ul style={{ textAlign: 'left', maxWidth: '500px' }}>
          <li>V7P3R Performance Analytics</li>
          <li>Tournament Results Processing</li>
          <li>AI-Powered Query Interface</li>
          <li>Engine Version Comparison</li>
          <li>Real-time Data Processing</li>
        </ul>
      </div>

      <div style={{ margin: '20px 0' }}>
        <h3>🛠️ System Information</h3>
        <div style={{ textAlign: 'left', maxWidth: '600px', fontSize: '14px' }}>
          <div><strong>Project:</strong> Chess Engine Metrics Agent</div>
          <div><strong>Version:</strong> 1.0.0</div>
          <div><strong>Build:</strong> Development</div>
          <div><strong>Data Source:</strong> V7P3R Tournament Results</div>
          <div><strong>AI Model:</strong> Custom Chess Engine Analysis</div>
        </div>
      </div>
      
      {!allServicesRunning && (
        <div style={{ margin: '20px 0', padding: '15px', backgroundColor: '#ff9800', color: 'white', borderRadius: '5px' }}>
          ⚠️ Some services are not ready. Please wait for all services to start.
        </div>
      )}
    </div>
  );
}

export default HealthCheck;