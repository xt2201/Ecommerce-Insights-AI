/**
 * Theme Configuration - Color Palette & Typography
 * Based on FRONTEND_UX_UI_PLAN.md Design System
 */

export const colors = {
  light: {
    primary: '#2563EB',      // Blue 600
    secondary: '#7C3AED',    // Purple 600
    success: '#10B981',      // Green 500
    warning: '#F59E0B',      // Amber 500
    danger: '#EF4444',       // Red 500
    neutral: '#64748B',      // Slate 600
    background: '#FFFFFF',   // White
    surface: '#F8FAFC',      // Slate 50
    border: '#E2E8F0',       // Slate 200
    text: {
      primary: '#1E293B',    // Slate 800
      secondary: '#64748B',  // Slate 600
      tertiary: '#94A3B8',   // Slate 400
    }
  },
  dark: {
    primary: '#3B82F6',      // Blue 500
    secondary: '#8B5CF6',    // Purple 500
    success: '#34D399',      // Green 400
    warning: '#FBBF24',      // Amber 400
    danger: '#F87171',       // Red 400
    neutral: '#94A3B8',      // Slate 400
    background: '#0F172A',   // Slate 900
    surface: '#1E293B',      // Slate 800
    border: '#334155',       // Slate 700
    text: {
      primary: '#F1F5F9',    // Slate 100
      secondary: '#CBD5E1',  // Slate 300
      tertiary: '#94A3B8',   // Slate 400
    }
  }
} as const;

export const typography = {
  fonts: {
    heading: 'var(--font-inter)',
    body: 'var(--font-inter)',
    mono: 'var(--font-jetbrains-mono)',
  },
  sizes: {
    h1: { size: '48px', weight: '700', lineHeight: '1.2' },
    h2: { size: '32px', weight: '600', lineHeight: '1.3' },
    h3: { size: '24px', weight: '600', lineHeight: '1.4' },
    large: { size: '18px', weight: '400', lineHeight: '1.6' },
    base: { size: '16px', weight: '400', lineHeight: '1.5' },
    small: { size: '14px', weight: '400', lineHeight: '1.5' },
    mono: { size: '16px', weight: '400', lineHeight: '1.5' },
  }
} as const;

export type ThemeMode = 'light' | 'dark';
export type ColorScheme = typeof colors.light;
