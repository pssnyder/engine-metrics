import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for managing auto-refresh and live data monitoring
 * Implements non-disruptive background updates
 */
export const useAutoRefresh = (refreshInterval = 30000) => { // 30 seconds default
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [hasNewData, setHasNewData] = useState(false);
  const [refreshCount, setRefreshCount] = useState(0);
  const [liveGames, setLiveGames] = useState([]);
  const [recentStats, setRecentStats] = useState(null);
  const intervalRef = useRef(null);
  const lastCheckedRef = useRef(Date.now());

  // Check for new data without disrupting user experience
  const checkForNewData = useCallback(async (silent = true) => {
    try {
      if (!silent) setIsRefreshing(true);

      const response = await fetch(
        `http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/checkNewData?lastChecked=${lastCheckedRef.current}`
      );
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.hasNewData) {
          setHasNewData(true);
          setLastUpdateTime(Date.now());
          lastCheckedRef.current = Date.now();
          
          // Also fetch updated live games
          await fetchLiveGames(true);
          await fetchRecentStats(true);
          
          return data;
        }
      }
      
      return { hasNewData: false };
    } catch (error) {
      console.warn('Error checking for new data:', error);
      return { hasNewData: false, error: error.message };
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  }, []);

  // Fetch current live games
  const fetchLiveGames = useCallback(async (silent = false) => {
    try {
      const response = await fetch('http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/getLiveGames');
      
      if (response.ok) {
        const data = await response.json();
        setLiveGames(data.liveGames || []);
        return data;
      }
    } catch (error) {
      if (!silent) console.error('Error fetching live games:', error);
      return { liveGames: [], error: error.message };
    }
  }, []);

  // Fetch recent statistics
  const fetchRecentStats = useCallback(async (silent = false) => {
    try {
      const response = await fetch('http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/getRecentStats?days=7');
      
      if (response.ok) {
        const data = await response.json();
        setRecentStats(data);
        return data;
      }
    } catch (error) {
      if (!silent) console.error('Error fetching recent stats:', error);
      return { error: error.message };
    }
  }, []);

  // Manual refresh trigger
  const manualRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setRefreshCount(prev => prev + 1);
    
    try {
      // Trigger backend refresh
      await fetch('http://127.0.0.1:5010/chess-engine-metrics-agent/us-central1/refreshMetrics', {
        method: 'POST'
      });
      
      // Check for new data
      await checkForNewData(false);
      
      setHasNewData(false); // Reset new data flag after manual refresh
    } catch (error) {
      console.error('Error during manual refresh:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [checkForNewData]);

  // Clear new data notification
  const clearNewDataFlag = useCallback(() => {
    setHasNewData(false);
  }, []);

  // Start/stop auto-refresh
  const startAutoRefresh = useCallback(() => {
    if (intervalRef.current) return;
    
    intervalRef.current = setInterval(async () => {
      await checkForNewData(true);
    }, refreshInterval);
  }, [checkForNewData, refreshInterval]);

  const stopAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Initialize and cleanup
  useEffect(() => {
    // Initial data fetch
    checkForNewData(true);
    fetchLiveGames(true);
    fetchRecentStats(true);
    
    // Start auto-refresh
    startAutoRefresh();

    return () => {
      stopAutoRefresh();
    };
  }, [checkForNewData, fetchLiveGames, fetchRecentStats, startAutoRefresh, stopAutoRefresh]);

  // Pause auto-refresh when user is actively interacting
  const pauseAutoRefresh = useCallback(() => {
    stopAutoRefresh();
    setTimeout(startAutoRefresh, 60000); // Resume after 1 minute
  }, [startAutoRefresh, stopAutoRefresh]);

  return {
    // Status
    lastUpdateTime,
    isRefreshing,
    hasNewData,
    refreshCount,
    
    // Data
    liveGames,
    recentStats,
    
    // Actions
    manualRefresh,
    clearNewDataFlag,
    pauseAutoRefresh,
    
    // Control
    startAutoRefresh,
    stopAutoRefresh,
    
    // Direct fetch functions
    checkForNewData: () => checkForNewData(false),
    fetchLiveGames: () => fetchLiveGames(false),
    fetchRecentStats: () => fetchRecentStats(false)
  };
};

export default useAutoRefresh;