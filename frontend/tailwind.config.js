/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Тёмная тема через data-attribute (tokens.css — dark-only)
  darkMode: 'class',
  theme: {
    extend: {
      // ── Цвета из токенов (CSS vars) ───────────────────────────────────────
      colors: {
        // Surfaces
        'bg-0': 'var(--bg-0)',
        'bg-1': 'var(--bg-1)',
        'bg-2': 'var(--bg-2)',
        'bg-3': 'var(--bg-3)',
        'bg-4': 'var(--bg-4)',
        // Borders
        'border-subtle':  'var(--border-subtle)',
        'border-default': 'var(--border)',
        'border-strong':  'var(--border-strong)',
        // Text
        'fg':        'var(--fg)',
        'fg-dim':    'var(--fg-dim)',
        'fg-mute':   'var(--fg-mute)',
        'fg-faint':  'var(--fg-faint)',
        // Brand & accent
        'brand':        'var(--brand)',
        'brand-ink':    'var(--brand-ink)',
        'accent':       'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        'accent-press': 'var(--accent-press)',
        'accent-faint': 'var(--accent-faint)',
        'accent-ink':   'var(--accent-ink)',
        // Semantic
        'ok':        'var(--ok)',
        'ok-faint':  'var(--ok-faint)',
        'warn':      'var(--warn)',
        'warn-faint':'var(--warn-faint)',
        'err':       'var(--err)',
        'err-faint': 'var(--err-faint)',
        'info':      'var(--info)',
        'info-faint':'var(--info-faint)',
      },
      // ── Типографика ──────────────────────────────────────────────────────
      fontFamily: {
        sans: 'var(--font-sans)',
        mono: 'var(--font-mono)',
      },
      fontSize: {
        '2xs': ['10px', { lineHeight: '14px' }],
        'xs':  ['11px', { lineHeight: '16px' }],
        'sm':  ['12.5px', { lineHeight: '18px' }],
        'base':['13px', { lineHeight: '20px' }],
        'md':  ['14px', { lineHeight: '20px' }],
        'lg':  ['15px', { lineHeight: '22px' }],
        'xl':  ['17px', { lineHeight: '24px' }],
      },
      // ── Высоты из density tokens ──────────────────────────────────────────
      height: {
        'row':    'var(--h-row)',
        'btn-sm': 'var(--h-btn-sm)',
        'btn-md': 'var(--h-btn-md)',
        'btn-lg': 'var(--h-btn-lg)',
        'input':  'var(--h-input)',
        'header': 'var(--h-header)',
        'hit':    'var(--hit-target)',
      },
      minHeight: {
        'hit': 'var(--hit-target)',
      },
      // ── Радиусы ───────────────────────────────────────────────────────────
      borderRadius: {
        'sm': 'var(--r-sm)',
        'md': 'var(--r-md)',
        'lg': 'var(--r-lg)',
      },
      // ── Тени ──────────────────────────────────────────────────────────────
      boxShadow: {
        'popover': 'var(--shadow-popover)',
        'modal':   'var(--shadow-modal)',
      },
      // ── Padding ──────────────────────────────────────────────────────────
      padding: {
        'card': 'var(--pad-card)',
      },
    },
  },
  plugins: [],
}
