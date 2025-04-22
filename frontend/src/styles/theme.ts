export const themes = {
  default: {
    primary: {
      from: '#3B82F6',
      to: '#2563EB',
      hover: '#1D4ED8'
    },
    secondary: {
      from: '#8B5CF6',
      to: '#6D28D9',
      hover: '#5B21B6'
    },
    accent: {
      from: '#EC4899',
      to: '#DB2777',
      hover: '#BE185D'
    },
    background: {
      primary: '#ffffff',
      secondary: '#f8fafc',
      dark: '#0f172a'
    }
  },
  cyberpunk: {
    primary: {
      from: '#FF0080',
      to: '#7928CA',
      hover: '#6B21A8'
    },
    secondary: {
      from: '#00ffd5',
      to: '#00b4d8',
      hover: '#0096c7'
    },
    accent: {
      from: '#f97316',
      to: '#ea580c',
      hover: '#c2410c'
    },
    background: {
      primary: '#030712',
      secondary: '#111827',
      dark: '#000000'
    }
  },
  ocean: {
    primary: {
      from: '#0EA5E9',
      to: '#0284C7',
      hover: '#0369A1'
    },
    secondary: {
      from: '#06B6D4',
      to: '#0891B2',
      hover: '#0E7490'
    },
    accent: {
      from: '#14B8A6',
      to: '#0D9488',
      hover: '#0F766E'
    },
    background: {
      primary: '#f0fdfa',
      secondary: '#ecfeff',
      dark: '#164e63'
    }
  }
} as const;

export type ThemeType = keyof typeof themes;