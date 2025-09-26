import React, { useState } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Box,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Divider,
} from '@mui/material';
import {
  Send,
  Psychology,
  TrendingUp,
  Compare,
  QuestionAnswer,
} from '@mui/icons-material';

function QueryInterface() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [queryHistory, setQueryHistory] = useState([]);

  const exampleQueries = [
    "How has V7P3R improved since v10.8?",
    "What caused the v10.7 performance drop?",
    "Which engine performs best in blitz?",
    "What are the key factors influencing engine performance?",
    "How do different time controls affect engine performance?",
    "Compare SlowMate vs V7P3R tactical strength"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);

    // Simulate AI processing
    setTimeout(() => {
      const mockResponse = {
        query: query,
        answer: generateMockAnswer(query),
        confidence: Math.floor(Math.random() * 20) + 80,
        sources: [
          "V7P3R v10.8 Tournament Results",
          "Engine Battle Analysis 2024-09",
          "Performance Metrics Database"
        ],
        relatedData: {
          gamesAnalyzed: Math.floor(Math.random() * 500) + 100,
          timeRange: "Last 3 months",
          engines: ["V7P3R", "SlowMate", "C0BR4"]
        }
      };

      setResponse(mockResponse);
      setQueryHistory(prev => [mockResponse, ...prev.slice(0, 4)]);
      setLoading(false);
      setQuery('');
    }, 2000);
  };

  const generateMockAnswer = (query) => {
    if (query.toLowerCase().includes('v7p3r') && query.toLowerCase().includes('improve')) {
      return "Based on analysis of 347 games, V7P3R has shown significant improvement since v10.8. Key improvements include: 15% better tactical accuracy in middlegame positions, improved endgame evaluation leading to 8% more wins in drawn positions, and enhanced opening book resulting in better position evaluation after move 15. The engine's ELO rating increased from 2480 to 2510, with particularly strong performance in rapid time controls.";
    }
    if (query.toLowerCase().includes('performance drop')) {
      return "The v10.7 performance drop was primarily caused by a regression in the evaluation function for pawn structure. Analysis shows a 12% decrease in positional understanding, particularly in closed positions. The issue was traced to changes in the piece-square tables that over-weighted material at the expense of positional factors. This resulted in the engine making suboptimal trades in strategic positions, leading to a 25-point ELO decrease.";
    }
    if (query.toLowerCase().includes('blitz')) {
      return "In blitz time controls, SlowMate currently performs best with a 68% win rate, followed by V7P3R at 65% and C0BR4 at 52%. SlowMate's strength comes from its optimized search algorithm that performs better under time pressure, while V7P3R sometimes overthinks positions in time-critical moments. The data shows SlowMate's tactical calculation speed gives it a significant advantage in blitz formats.";
    }
    return "Based on the available data, I've analyzed the patterns in your chess engine performance. The key factors show significant correlations with tactical accuracy, endgame evaluation, and time management efficiency. Would you like me to elaborate on any specific aspect of this analysis?";
  };

  const handleExampleQuery = (exampleQuery) => {
    setQuery(exampleQuery);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        AI Chess Engine Analysis
      </Typography>
      
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Ask questions about your chess engines' performance, compare versions, 
        and get AI-powered insights from your data.
      </Typography>

      <Grid container spacing={4}>
        {/* Query Input */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box component="form" onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Ask a question about your chess engines"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., How has V7P3R improved since the last version?"
                  sx={{ mb: 2 }}
                />
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="textSecondary">
                    {query.length}/500 characters
                  </Typography>
                  <Button
                    type="submit"
                    variant="contained"
                    startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                    disabled={loading || !query.trim()}
                  >
                    {loading ? 'Analyzing...' : 'Ask AI'}
                  </Button>
                </Box>
              </Box>

              {/* Example Queries */}
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Example Questions:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {exampleQueries.map((example, index) => (
                    <Chip
                      key={index}
                      label={example}
                      variant="outlined"
                      size="small"
                      onClick={() => handleExampleQuery(example)}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* AI Response */}
          {response && (
            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Psychology color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    AI Analysis Result
                  </Typography>
                  <Chip 
                    label={`${response.confidence}% confidence`} 
                    color="success" 
                    size="small" 
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    Query: {response.query}
                  </Typography>
                </Alert>

                <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7 }}>
                  {response.answer}
                </Typography>

                <Divider sx={{ my: 2 }} />

                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                      Data Sources:
                    </Typography>
                    {response.sources.map((source, index) => (
                      <Typography key={index} variant="body2" color="textSecondary">
                        • {source}
                      </Typography>
                    ))}
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                      Analysis Details:
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      • Games Analyzed: {response.relatedData.gamesAnalyzed}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      • Time Range: {response.relatedData.timeRange}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      • Engines: {response.relatedData.engines.join(', ')}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          {/* Quick Actions */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<TrendingUp />}
                  onClick={() => handleExampleQuery("Show V7P3R performance trends")}
                >
                  Performance Trends
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Compare />}
                  onClick={() => handleExampleQuery("Compare all engines")}
                >
                  Engine Comparison
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<QuestionAnswer />}
                  onClick={() => handleExampleQuery("What should I improve next?")}
                >
                  Improvement Suggestions
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Recent Queries */}
          {queryHistory.length > 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Queries
                </Typography>
                {queryHistory.map((item, index) => (
                  <Box key={index} sx={{ mb: 2, p: 2, backgroundColor: '#2a2a2a', borderRadius: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                      {item.query}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Confidence: {item.confidence}%
                    </Typography>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Container>
  );
}

export default QueryInterface;