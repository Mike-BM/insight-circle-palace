/* Insight Circle Palace: the ONE Tailwind configuration used by every page.
   (Previously 11 slightly different copies were pasted into individual pages.) */
tailwind.config = {
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#080E1E', dark: '#050914', light: '#10172A' },
        surface: { DEFAULT: '#0D1629', 2: '#121D36' },
        gold: { DEFAULT: '#D4A345', light: '#F5D38A', dark: '#A37722' },
        cream: '#FAF7F2',
        'navy-dark': '#050914',
        'navy-light': '#10172A',
        'gold-light': '#F5D38A',
        'gold-dark': '#A37722',
        'brand-navy': '#14213d',
        'brand-gold': '#a86a1c',
        heal: { blue: '#3b82f6', purple: '#8b5cf6', pink: '#ec4899', indigo: '#6366f1' },
        pink: { 400: '#f472b6', 500: '#ec4899', 600: '#db2777' },
        sage: { 400: '#9ca3af', 500: '#84cc16', 600: '#65a30d' }
      },
      fontFamily: {
        display: ['"Plus Jakarta Sans"', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
        serif: ['"Playfair Display"', 'serif']
      }
    }
  }
};
