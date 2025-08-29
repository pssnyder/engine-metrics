import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout
});

// Add request interceptor to log requests in development
if (process.env.NODE_ENV === 'development') {
  api.interceptors.request.use(request => {
    console.log('Starting Request:', request.url);
    return request;
  });
}

// Add response interceptor to handle errors
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Health and status
  getHealth: () => api.get('/health'),
  getStatus: () => api.get('/status'),

  // Metrics
  getMetricsSummary: (forceRefresh = false) => 
    api.get('/metrics/summary', { params: { force_refresh: forceRefresh } }),
  getEngineMetrics: (engineName) => 
    api.get(`/metrics/engines/${engineName}`),
  getHeadToHeadMetrics: () => 
    api.get('/metrics/head-to-head'),
  getRecentPerformance: (days = 30) => 
    api.get('/metrics/recent-performance', { params: { days } }),
  refreshMetrics: () => 
    api.post('/metrics/refresh'),

  // Games
  getRecentGames: (limit = 50) => 
    api.get('/games/recent', { params: { limit } }),
  searchGames: (filters) => 
    api.get('/games/search', { params: filters }),
  getGameDetails: (gameId) => 
    api.get(`/games/${gameId}`),
  getGamesOverview: () => 
    api.get('/games/stats/overview'),

  // Configuration
  getSettings: () => 
    api.get('/config/settings'),
  getMonitoredDirectories: () => 
    api.get('/config/directories'),
  getEngineConfig: () => 
    api.get('/config/engines'),
};

export default apiService;
