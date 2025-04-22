'use client';

import { createContext, useContext, ReactNode } from 'react';

// Single beautiful theme with carefully selected colors
const theme = {
  colors: {
    primary: '#3B82F6',    // Blue
    secondary: '#8B5CF6',  // Purple
    accent: '#EC4899',     // Pink
    
    background: '#ffffff',
    cardBg: '#f8fafc',
    border: '#e2e8f0',
    
    text: '#0f172a',
    textSecondary: '#334155',
    textMuted: '#64748b',
    
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#0EA5E9'
  }
};

const ThemeContext = createContext(theme);

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  return useContext(ThemeContext);
};