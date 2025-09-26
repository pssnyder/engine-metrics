import React, { useState } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Box,
  Chip,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import {
  ExpandMore,
  TrendingUp,
  TrendingDown,
  Remove,
} from '@mui/icons-material';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

function EngineComparison() {
  const [selectedEngines, setSelectedEngines] = useState(['V7P3R', 'SlowMate', 'C0BR4']);

  const engineData = {
    'V7P3R': {
      version: 'v10.9',
      elo: 2510,
      winRate: 65,
      drawRate: 25,
      lossRate: 10,
      tacticalAccuracy: 92,
      positionalUnderstanding: 88,
      endgameStrength: 85,
      openingBook: 90,
      timeManagement: 82,
      recentTrend: 'up',
      trendValue: '+30 ELO',
      gamesPlayed: 547,
      lastUpdated: '2024-09-14'
    },
    'SlowMate': {
      version: 'v2.1',
      elo: 2485,
      winRate: 58,
      drawRate: 32,
      lossRate: 10,
      tacticalAccuracy: 89,
      positionalUnderstanding: 91,
      endgameStrength: 88,
      openingBook: 85,
      timeManagement: 95,
      recentTrend: 'up',
      trendValue: '+15 ELO',
      gamesPlayed: 423,
      lastUpdated: '2024-09-13'
    },
    'C0BR4': {
      version: 'v1.3',
      elo: 2420,
      winRate: 45,
      drawRate: 35,
      lossRate: 20,
      tacticalAccuracy: 85,
      positionalUnderstanding: 83,
      endgameStrength: 80,
      openingBook: 88,
      timeManagement: 78,
      recentTrend: 'down',
      trendValue: '-12 ELO',
      gamesPlayed: 298,
      lastUpdated: '2024-09-12'
    }
  };

  const radarData = {
    labels: [
      'Tactical Accuracy',
      'Positional Understanding',
      'Endgame Strength',
      'Opening Book',
      'Time Management'
    ],
    datasets: selectedEngines.map((engine, index) => ({
      label: engine,
      data: [
        engineData[engine].tacticalAccuracy,
        engineData[engine].positionalUnderstanding,
        engineData[engine].endgameStrength,
        engineData[engine].openingBook,
        engineData[engine].timeManagement
      ],
      backgroundColor: [
        'rgba(25, 118, 210, 0.2)',
        'rgba(220, 0, 78, 0.2)',
        'rgba(255, 152, 0, 0.2)'
      ][index],
      borderColor: [
        '#1976d2',
        '#dc004e',
        '#ff9800'
      ][index],
      pointBackgroundColor: [
        '#1976d2',
        '#dc004e',
        '#ff9800'
      ][index],
    }))
  };

  const getTrendIcon = (trend) => {
    switch(trend) {
      case 'up': return <TrendingUp color="success" />;
      case 'down': return <TrendingDown color="error" />;
      default: return <Remove color="disabled" />;
    }
  };

  const getTrendColor = (trend) => {
    switch(trend) {
      case 'up': return 'success';
      case 'down': return 'error';
      default: return 'default';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Engine Performance Comparison
      </Typography>
      
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Compare the performance characteristics of your chess engines across 
        multiple dimensions and metrics.
      </Typography>

      {/* Engine Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {selectedEngines.map((engineName) => {
          const engine = engineData[engineName];
          return (
            <Grid item xs={12} md={4} key={engineName}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h5" sx={{ flexGrow: 1 }}>
                      {engineName}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getTrendIcon(engine.recentTrend)}
                      <Chip 
                        label={engine.trendValue} 
                        size="small" 
                        color={getTrendColor(engine.recentTrend)}
                        sx={{ ml: 1 }}
                      />
                    </Box>
                  </Box>
                  
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Version {engine.version}
                  </Typography>
                  
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="h4" color="primary">
                      {engine.elo}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      ELO Rating
                    </Typography>
                  </Box>

                  <Grid container spacing={1}>
                    <Grid item xs={4}>
                      <Typography variant="h6" color="success.main">
                        {engine.winRate}%
                      </Typography>
                      <Typography variant="caption">Wins</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h6" color="warning.main">
                        {engine.drawRate}%
                      </Typography>
                      <Typography variant="caption">Draws</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h6" color="error.main">
                        {engine.lossRate}%
                      </Typography>
                      <Typography variant="caption">Losses</Typography>
                    </Grid>
                  </Grid>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="textSecondary">
                      {engine.gamesPlayed} games • Updated {engine.lastUpdated}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Radar Chart */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Performance Radar Analysis
          </Typography>
          <Box sx={{ height: 400 }}>
            <Radar 
              data={radarData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    labels: { color: '#ffffff' }
                  }
                },
                scales: {
                  r: {
                    angleLines: { color: '#555' },
                    grid: { color: '#555' },
                    pointLabels: { color: '#ffffff' },
                    ticks: { color: '#ffffff' },
                    min: 0,
                    max: 100
                  }
                }
              }}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Detailed Comparison Table */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Detailed Performance Metrics
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Metric</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">{engine}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>ELO Rating</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">
                      <Typography variant="h6" color="primary">
                        {engineData[engine].elo}
                      </Typography>
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell>Tactical Accuracy</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">
                      <Box>
                        <Typography variant="body2">
                          {engineData[engine].tacticalAccuracy}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={engineData[engine].tacticalAccuracy} 
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell>Positional Understanding</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">
                      <Box>
                        <Typography variant="body2">
                          {engineData[engine].positionalUnderstanding}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={engineData[engine].positionalUnderstanding} 
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell>Endgame Strength</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">
                      <Box>
                        <Typography variant="body2">
                          {engineData[engine].endgameStrength}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={engineData[engine].endgameStrength} 
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
                <TableRow>
                  <TableCell>Time Management</TableCell>
                  {selectedEngines.map(engine => (
                    <TableCell key={engine} align="center">
                      <Box>
                        <Typography variant="body2">
                          {engineData[engine].timeManagement}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={engineData[engine].timeManagement} 
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Detailed Analysis */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">AI Analysis & Recommendations</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body1" sx={{ mb: 2 }}>
            <strong>Key Findings:</strong>
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            • <strong>V7P3R</strong> leads in overall performance with the highest ELO (2510) and strong tactical accuracy (92%).
            Recent improvements show consistent upward trend (+30 ELO).
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            • <strong>SlowMate</strong> excels in time management (95%) and positional understanding (91%), 
            making it particularly effective in blitz and rapid formats.
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            • <strong>C0BR4</strong> shows room for improvement across all metrics but has a solid opening book (88%).
            Recent decline (-12 ELO) suggests need for tactical training focus.
          </Typography>
          
          <Typography variant="body1" sx={{ mt: 3, mb: 2 }}>
            <strong>Recommendations:</strong>
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            • Focus V7P3R development on time management optimization
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            • Enhance SlowMate's tactical calculation depth
          </Typography>
          <Typography variant="body2">
            • Prioritize C0BR4's endgame evaluation improvements
          </Typography>
        </AccordionDetails>
      </Accordion>
    </Container>
  );
}

export default EngineComparison;