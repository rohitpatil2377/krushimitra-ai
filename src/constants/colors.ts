// Single source of truth for colors. Friendly, high-contrast, farming-themed.
// Large readable text + clear contrast helps low-vision users and bright sunlight.
export const Colors = {
  primary: '#2E7D32', // leaf green
  primaryDark: '#1B5E20',
  accent: '#F9A825', // harvest yellow
  bg: '#F4F8F1', // soft off-white-green background
  card: '#FFFFFF',
  text: '#1A1A1A',
  textMuted: '#5C6B57',
  border: '#E2E9DD',
  danger: '#C62828',
  white: '#FFFFFF',
} as const;

export type ColorName = keyof typeof Colors;
