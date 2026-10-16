/** @type {import('tailwindcss').Config} */
/*
 * music2chart industrial design tokens (Dark Anodized Chassis).
 * Source of truth: design_specification_music2chart_ui.md
 *  - Zero rounded corners: every borderRadius token resolves to 0.
 *  - No generic gradients: lighting comes only from functional LEDs.
 *  - Technical mono typography with open tracking.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // Override (not extend) so `rounded-*` utilities can never produce curves.
    borderRadius: {
      none: '0',
      DEFAULT: '0',
      sm: '0',
      md: '0',
      lg: '0',
      xl: '0',
      '2xl': '0',
      '3xl': '0',
      // Only physical round hardware (LED lenses, screw heads, knob caps) may use this.
      full: '9999px',
    },
    fontFamily: {
      mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      grotesk: ['"Space Grotesk"', '"JetBrains Mono"', 'ui-sans-serif', 'sans-serif'],
      sans: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
    },
    extend: {
      colors: {
        chassis: '#0D0E11',
        panel: '#14161B',
        module: '#1A1D24',
        hw: {
          border: '#2A2E39',
          screw: '#434958',
        },
        silk: {
          DEFAULT: '#E6E8EE',
          dim: '#8E95A5',
          neutral: '#A1A7B5',
        },
        fret: {
          green: '#00E676',
          red: '#FF1744',
          yellow: '#FFEA00',
          blue: '#2979FF',
          orange: '#FF9100',
          open: '#9D4EDD',
        },
        starpower: '#00E5FF',
      },
      letterSpacing: {
        silk: '0.08em',
        'silk-wide': '0.12em',
      },
      fontSize: {
        micro: ['0.625rem', { lineHeight: '0.875rem' }],
      },
      boxShadow: {
        // Machined bevels — light from top-left, no blur halos.
        bevel: 'inset 1px 1px 0 rgba(255,255,255,0.05), inset -1px -1px 0 rgba(0,0,0,0.55)',
        recess: 'inset 1px 1px 0 rgba(0,0,0,0.6), inset -1px -1px 0 rgba(255,255,255,0.04)',
        lift: '0 1px 0 rgba(0,0,0,0.6), 0 2px 0 rgba(0,0,0,0.35)',
      },
      keyframes: {
        'led-blink': {
          '0%, 55%': { opacity: '1' },
          '56%, 100%': { opacity: '0.08' },
        },
      },
      animation: {
        'led-blink': 'led-blink 1s steps(1, end) infinite',
        'led-blink-fast': 'led-blink 0.35s steps(1, end) infinite',
      },
    },
  },
  plugins: [],
};
