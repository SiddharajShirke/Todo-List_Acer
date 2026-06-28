import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getTodayStats } from '../services/api';
import { useAuth } from './AuthContext';

const StatsContext = createContext();

export function StatsProvider({ children }) {
  const { user } = useAuth();
  const [todayStats, setTodayStats] = useState(null);

  const refreshStats = useCallback(async () => {
    if (!user) {
      setTodayStats(null);
      return;
    }
    try {
      const stats = await getTodayStats();
      setTodayStats(stats);
    } catch (e) {
      console.error('Failed to fetch today stats:', e);
    }
  }, [user]);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  return (
    <StatsContext.Provider value={{ todayStats, refreshStats }}>
      {children}
    </StatsContext.Provider>
  );
}

export const useStats = () => useContext(StatsContext);
