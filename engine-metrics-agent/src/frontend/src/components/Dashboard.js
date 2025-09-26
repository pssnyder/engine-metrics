import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  CircularProgress,
} from '@mui/material';
import {
  Line,
  Bar,
  Doughnut,
} from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    // Simulate loading dashboard data
    setTimeout(() => {
      setDashboardData({
        totalGames: 1247,
        totalEngines: 3,
        lastUpdated: new Date().toLocaleDateString(),
        recentQueries: 15,
      });
      setLoading(false);
    }, 1000);
  }, []);

  const performanceData = {
    labels: ['V7P3R v10.6', 'V7P3R v10.7', 'V7P3R v10.8', 'V7P3R v10.9'],
    datasets: [
      {
        label: 'ELO Rating',
        data: [2450, 2420, 2480, 2510],
        borderColor: '#1976d2',
        backgroundColor: 'rgba(25, 118, 210, 0.1)',
        tension: 0.4,
      },
    ],
  };

  const engineComparisonData = {
    labels: ['V7P3R', 'SlowMate', 'C0BR4'],
    datasets: [
      {
        label: 'Win Rate %',
        data: [65, 58, 45],
        backgroundColor: ['#1976d2', '#dc004e', '#ff9800'],
      },
    ],
  };

  const gameDistributionData = {
    labels: ['Blitz', 'Rapid', 'Classical'],
    datasets: [
      {
        data: [45, 35, 20],
        backgroundColor: ['#4caf50', '#2196f3', '#ff9800'],
      },
    ],
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading Dashboard...
        </Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Chess Engine Performance Dashboard
      </Typography>
      
      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Games
              </Typography>
              <Typography variant="h4">
                {dashboardData.totalGames.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Engines Tracked
              </Typography>
              <Typography variant="h4">
                {dashboardData.totalEngines}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Recent AI Queries
              </Typography>
              <Typography variant="h4">
                {dashboardData.recentQueries}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Last Updated
              </Typography>
              <Typography variant="h6">
                {dashboardData.lastUpdated}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                V7P3R Performance Over Time
              </Typography>
              <Box sx={{ height: 300 }}>
                <Line 
                  data={performanceData} 
                  options={{ 
                    responsive: true, 
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        labels: { color: '#ffffff' }
                      }
                    },
                    scales: {
                      x: { ticks: { color: '#ffffff' } },
                      y: { ticks: { color: '#ffffff' } }
                    }
                  }} 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Game Time Distribution
              </Typography>
              <Box sx={{ height: 300 }}>
                <Doughnut 
                  data={gameDistributionData} 
                  options={{ 
                    responsive: true, 
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        labels: { color: '#ffffff' }
                      }
                    }
                  }} 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Engine Win Rate Comparison
              </Typography>
              <Box sx={{ height: 300 }}>
                <Bar 
                  data={engineComparisonData} 
                  options={{ 
                    responsive: true, 
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        labels: { color: '#ffffff' }
                      }
                    },
                    scales: {
                      x: { ticks: { color: '#ffffff' } },
                      y: { ticks: { color: '#ffffff' } }
                    }
                  }} 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}

export default Dashboard;