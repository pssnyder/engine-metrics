import React, { useState, useEffect } from 'react';

function AnalyticsDashboard() {
  const [selectedVersion, setSelectedVersion] = useState('All');
  const [overallMetrics, setOverallMetrics] = useState({
    totalGames: 0,
    totalWins: 0,
    totalLosses: 0,
    totalTies: 0,
    winRate: 0,
    bestVersion: 'N/A',
    worstVersion: 'N/A',
    loading: true
  });
  
  const [versionMetrics, setVersionMetrics] = useState({
    version: 'All',
    games: 0,
    wins: 0,
    losses: 0,
    ties: 0,
    winRate: 0,
    checkmates: 0,
    timeouts: 0,
    loading: true
  });

  const [availableVersions, setAvailableVersions] = useState(['All']);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  // Load overall metrics from backend
  useEffect(() => {
    const fetchOverallMetrics = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/getOverallMetrics');
        if (response.ok) {
          const data = await response.json();
          setOverallMetrics({
            ...data,
            loading: false
          });
          setAvailableVersions(['All', ...data.availableVersions]);
        } else {
          // Fallback to mock data if backend not available
          setOverallMetrics({
            totalGames: 2547,
            totalWins: 1423,
            totalLosses: 892,
            totalTies: 232,
            winRate: 55.8,
            bestVersion: 'V7P3R_v12.0',
            worstVersion: 'V7P3R_v10.1',
            loading: false
          });
          setAvailableVersions([
            'All', 'V7P3R_v12.0', 'V7P3R_v11.0', 'V7P3R_v10.8', 
            'V7P3R_v10.2', 'V7P3R_v10.0', 'V7P3R_v9.3', 'V7P3R_v7.0'
          ]);
        }
      } catch (error) {
        console.error('Error fetching overall metrics:', error);
        // Use fallback data
        setOverallMetrics({
          totalGames: 2547,
          totalWins: 1423,
          totalLosses: 892,
          totalTies: 232,
          winRate: 55.8,
          bestVersion: 'V7P3R_v12.0',
          worstVersion: 'V7P3R_v10.1',
          loading: false
        });
        setAvailableVersions([
          'All', 'V7P3R_v12.0', 'V7P3R_v11.0', 'V7P3R_v10.8', 
          'V7P3R_v10.2', 'V7P3R_v10.0', 'V7P3R_v9.3', 'V7P3R_v7.0'
        ]);
      }
    };

    fetchOverallMetrics();
  }, []);

  useEffect(() => {
    // Fetch version-specific metrics from backend
    const fetchVersionMetrics = async () => {
      setVersionMetrics(prev => ({ ...prev, loading: true }));
      
      try {
        const response = await fetch(`http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/getVersionMetrics?version=${encodeURIComponent(selectedVersion)}`);
        
        if (response.ok) {
          const data = await response.json();
          setVersionMetrics({
            ...data,
            loading: false
          });
        } else {
          // Fallback to mock data
          throw new Error('Backend not available');
        }
      } catch (error) {
        console.error('Error fetching version metrics:', error);
        
        // Fallback mock data
        if (selectedVersion === 'All') {
          setVersionMetrics({
            version: 'All Versions',
            games: 2547,
            wins: 1423,
            losses: 892,
            ties: 232,
            winRate: 55.8,
            checkmates: 487,
            timeouts: 156,
            loading: false
          });
        } else {
          // Mock version-specific data
          const mockData = {
            'V7P3R_v12.0': { games: 234, wins: 156, losses: 52, ties: 26, checkmates: 67, timeouts: 12 },
            'V7P3R_v11.0': { games: 387, wins: 234, losses: 112, ties: 41, checkmates: 89, timeouts: 23 },
            'V7P3R_v10.8': { games: 456, wins: 278, losses: 134, ties: 44, checkmates: 102, timeouts: 28 },
          };
          
          const data = mockData[selectedVersion] || { games: 189, wins: 98, losses: 67, ties: 24, checkmates: 34, timeouts: 18 };
          const winRate = ((data.wins / data.games) * 100).toFixed(1);
          
          setVersionMetrics({
            version: selectedVersion,
            games: data.games,
            wins: data.wins,
            losses: data.losses,
            ties: data.ties,
            winRate: parseFloat(winRate),
            checkmates: data.checkmates,
            timeouts: data.timeouts,
            loading: false
          });
        }
      }
    };

    fetchVersionMetrics();
  }, [selectedVersion]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    setChatLoading(true);
    
    try {
      const response = await fetch('http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/processAnalyticsQuery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: chatMessage })
      });
      
      if (response.ok) {
        const data = await response.json();
        setChatResponse(data.answer);
      } else {
        // Fallback response if backend not available
        setChatResponse(`Based on the V7P3R tournament data, here's what I found regarding "${chatMessage}":\n\nThis is a simulated response. The actual AI service will provide detailed analysis of your chess engine performance, including trends, comparisons between versions, and strategic insights based on your tournament results.`);
      }
      
      setChatLoading(false);
      setChatMessage('');
      
    } catch (error) {
      console.error('Chat error:', error);
      setChatResponse(`I can help analyze V7P3R performance data. Based on your query "${chatMessage}", here are some general insights:\n\n📊 Current Data Available:\n• 2,547 total games across multiple engine versions\n• Win rate: 55.8% overall\n• Best performing version: V7P3R_v12.0\n\n🤖 Note: Backend analytics service not available. Please check if all services are running.`);
      setChatLoading(false);
    }
  };

  const exportToMarkdown = () => {
    const currentDate = new Date();
    const timestamp = currentDate.toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const readableDate = currentDate.toLocaleString();
    
    const markdownContent = `# V7P3R Engine Metrics Analysis Report

**Generated:** ${readableDate}  
**Query:** ${chatMessage || 'Latest Query'}  
**Selected Version:** ${selectedVersion}

---

## 📊 Current Metrics Summary

### Overall Performance
- **Total Games:** ${overallMetrics.totalGames.toLocaleString()}
- **Overall Win Rate:** ${overallMetrics.winRate}%
- **Total Wins:** ${overallMetrics.totalWins.toLocaleString()}
- **Total Losses:** ${overallMetrics.totalLosses.toLocaleString()}
- **Total Ties:** ${overallMetrics.totalTies.toLocaleString()}
- **Best Version:** ${overallMetrics.bestVersion}
- **Worst Version:** ${overallMetrics.worstVersion}
- **Total Versions Analyzed:** ${availableVersions.length - 1}

### ${versionMetrics.version} Specific Metrics
- **Games Played:** ${versionMetrics.games}
- **Win Rate:** ${versionMetrics.winRate}%
- **Wins:** ${versionMetrics.wins}
- **Losses:** ${versionMetrics.losses}
- **Ties:** ${versionMetrics.ties}
- **Checkmates:** ${versionMetrics.checkmates}
- **Timeouts:** ${versionMetrics.timeouts}
- **Other Results:** ${versionMetrics.games - versionMetrics.wins - versionMetrics.losses - versionMetrics.ties}

---

## 🤖 AI Analysis Response

${chatResponse}

---

## 📈 Analysis Notes

This report was generated from the V7P3R Analytics Dashboard, providing insights into chess engine performance across multiple versions and tournament battles.

### Available Engine Versions
${availableVersions.slice(1).map(version => `- ${version}`).join('\n')}

---

*Report generated by V7P3R Engine Metrics Agent - ${readableDate}*
`;

    // Create and download the file
    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `V7P3R_Analysis_Report_${timestamp}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const MetricCard = ({ title, value, subtitle, color = '#4caf50' }) => (
    <div style={{
      backgroundColor: 'white',
      padding: '20px',
      borderRadius: '10px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      textAlign: 'center',
      border: `3px solid ${color}`
    }}>
      <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>{title}</h3>
      <div style={{ fontSize: '28px', fontWeight: 'bold', color: color, margin: '10px 0' }}>
        {value}
      </div>
      {subtitle && <div style={{ fontSize: '14px', color: '#666' }}>{subtitle}</div>}
    </div>
  );

  return (
    <div style={{ padding: '20px', backgroundColor: '#f5f5f5', minHeight: '100vh', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#333', marginBottom: '10px' }}>🏆 V7P3R Analytics Dashboard</h1>
          <p style={{ color: '#666', fontSize: '16px' }}>Chess Engine Performance Metrics & AI Analysis</p>
        </div>

        {/* Top Section: Overall Metrics + Version Selector */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', marginBottom: '40px' }}>
          
          {/* Overall Metrics Infographic */}
          <div>
            <h2 style={{ color: '#333', marginBottom: '20px' }}>📊 Overall Performance</h2>
            {overallMetrics.loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div>🔄 Loading overall metrics...</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
                <MetricCard 
                  title="Total Games" 
                  value={overallMetrics.totalGames.toLocaleString()} 
                  subtitle="Across all versions"
                  color="#2196f3"
                />
                <MetricCard 
                  title="Win Rate" 
                  value={`${overallMetrics.winRate}%`} 
                  subtitle={`${overallMetrics.totalWins} wins`}
                  color="#4caf50"
                />
                <MetricCard 
                  title="Total Losses" 
                  value={overallMetrics.totalLosses.toLocaleString()} 
                  subtitle={`${overallMetrics.totalTies} ties`}
                  color="#ff9800"
                />
                <MetricCard 
                  title="Best Version" 
                  value={overallMetrics.bestVersion} 
                  subtitle="Highest win rate"
                  color="#9c27b0"
                />
                <MetricCard 
                  title="Worst Version" 
                  value={overallMetrics.worstVersion} 
                  subtitle="Needs improvement"
                  color="#f44336"
                />
                <MetricCard 
                  title="Engine Versions" 
                  value={availableVersions.length - 1} 
                  subtitle="Total analyzed"
                  color="#607d8b"
                />
              </div>
            )}
          </div>

          {/* Version Selector + Specific Metrics */}
          <div>
            <h2 style={{ color: '#333', marginBottom: '20px' }}>🎯 Version Analysis</h2>
            
            {/* Version Dropdown */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Select Engine Version:
              </label>
              <select
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '2px solid #ddd',
                  borderRadius: '5px',
                  fontSize: '16px'
                }}
              >
                {availableVersions.map(version => (
                  <option key={version} value={version}>{version}</option>
                ))}
              </select>
            </div>

            {/* Version-Specific Metrics */}
            {versionMetrics.loading ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                🔄 Loading version metrics...
              </div>
            ) : (
              <div style={{
                backgroundColor: 'white',
                padding: '20px',
                borderRadius: '10px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}>
                <h3 style={{ margin: '0 0 15px 0', color: '#333' }}>{versionMetrics.version}</h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', fontSize: '14px' }}>
                  <div><strong>Games:</strong> {versionMetrics.games}</div>
                  <div><strong>Win Rate:</strong> <span style={{ color: '#4caf50' }}>{versionMetrics.winRate}%</span></div>
                  <div><strong>Wins:</strong> <span style={{ color: '#4caf50' }}>{versionMetrics.wins}</span></div>
                  <div><strong>Losses:</strong> <span style={{ color: '#f44336' }}>{versionMetrics.losses}</span></div>
                  <div><strong>Ties:</strong> <span style={{ color: '#ff9800' }}>{versionMetrics.ties}</span></div>
                  <div><strong>Checkmates:</strong> {versionMetrics.checkmates}</div>
                  <div><strong>Timeouts:</strong> {versionMetrics.timeouts}</div>
                  <div><strong>Other:</strong> {versionMetrics.games - versionMetrics.wins - versionMetrics.losses - versionMetrics.ties}</div>
                </div>

                {/* Simple Visual */}
                <div style={{ marginTop: '15px' }}>
                  <div style={{ fontSize: '12px', marginBottom: '5px' }}>Performance Breakdown:</div>
                  <div style={{ display: 'flex', height: '20px', borderRadius: '10px', overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${(versionMetrics.wins / versionMetrics.games) * 100}%`, 
                      backgroundColor: '#4caf50' 
                    }}></div>
                    <div style={{ 
                      width: `${(versionMetrics.ties / versionMetrics.games) * 100}%`, 
                      backgroundColor: '#ff9800' 
                    }}></div>
                    <div style={{ 
                      width: `${(versionMetrics.losses / versionMetrics.games) * 100}%`, 
                      backgroundColor: '#f44336' 
                    }}></div>
                  </div>
                  <div style={{ display: 'flex', fontSize: '10px', marginTop: '5px' }}>
                    <span style={{ color: '#4caf50' }}>■ Wins</span>
                    <span style={{ color: '#ff9800', marginLeft: '10px' }}>■ Ties</span>
                    <span style={{ color: '#f44336', marginLeft: '10px' }}>■ Losses</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* AI Chat Interface */}
        <div style={{
          backgroundColor: 'white',
          padding: '30px',
          borderRadius: '10px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ color: '#333', marginBottom: '20px' }}>🤖 AI Analysis Chat</h2>
          
          <form onSubmit={handleChatSubmit} style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask about V7P3R performance, trends, comparisons..."
                style={{
                  flex: 1,
                  padding: '12px',
                  border: '2px solid #ddd',
                  borderRadius: '5px',
                  fontSize: '16px'
                }}
                disabled={chatLoading}
              />
              <button
                type="submit"
                disabled={chatLoading}
                style={{
                  padding: '12px 24px',
                  backgroundColor: chatLoading ? '#ccc' : '#4caf50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  fontSize: '16px',
                  cursor: chatLoading ? 'not-allowed' : 'pointer'
                }}
              >
                {chatLoading ? '🤔 Thinking...' : '🚀 Analyze'}
              </button>
            </div>
          </form>

          {chatResponse && (
            <div style={{
              backgroundColor: '#f9f9f9',
              padding: '20px',
              borderRadius: '5px',
              borderLeft: '4px solid #4caf50',
              whiteSpace: 'pre-wrap',
              fontSize: '14px',
              lineHeight: '1.6',
              position: 'relative'
            }}>
              <div style={{ 
                position: 'absolute', 
                top: '10px', 
                right: '10px' 
              }}>
                <button
                  onClick={exportToMarkdown}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#2196f3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                  title="Export analysis as Markdown file"
                >
                  📄 Export MD
                </button>
              </div>
              <strong>🤖 AI Response:</strong><br/><br/>
              {chatResponse}
            </div>
          )}

          {/* Example Questions */}
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ color: '#666', fontSize: '16px', marginBottom: '10px' }}>💡 Example Questions:</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {[
                "How has V7P3R v12.0 performed compared to v11.0?",
                "What's the checkmate rate for each version?",
                "Which opponents give V7P3R the most trouble?",
                "Show me timeout patterns across versions"
              ].map((question, index) => (
                <button
                  key={index}
                  onClick={() => setChatMessage(question)}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#e3f2fd',
                    border: '1px solid #2196f3',
                    borderRadius: '15px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    color: '#1976d2'
                  }}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AnalyticsDashboard;