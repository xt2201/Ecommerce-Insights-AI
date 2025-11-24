/**
 * Component Configuration - Reusable Component Props
 * Based on FRONTEND_UX_UI_PLAN.md Design System
 */

export const buttonSizes = {
  sm: {
    padding: '8px 16px',
    fontSize: '14px',
    height: '32px',
  },
  md: {
    padding: '12px 24px',
    fontSize: '16px',
    height: '40px',
  },
  lg: {
    padding: '16px 32px',
    fontSize: '18px',
    height: '48px',
  },
} as const;

export const inputSizes = {
  sm: {
    padding: '8px 12px',
    fontSize: '14px',
    height: '32px',
  },
  md: {
    padding: '12px 16px',
    fontSize: '16px',
    height: '40px',
  },
  lg: {
    padding: '16px 20px',
    fontSize: '18px',
    height: '48px',
  },
} as const;

export const cardPadding = {
  sm: '12px',
  md: '16px',
  lg: '24px',
} as const;

export const transitions = {
  fast: '150ms ease-in-out',
  base: '200ms ease-in-out',
  slow: '300ms ease-in-out',
} as const;

export const maxWidths = {
  prose: '65ch',        // Optimal reading width
  container: '1280px',  // Max content width
  modal: '600px',       // Modal max width
  wide: '1536px',       // Wide layouts
} as const;
