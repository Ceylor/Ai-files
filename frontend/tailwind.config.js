/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-space)", "var(--font-inter)", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // Глубокий тёмный фон.
        night: {
          950: "#0a0a0f",
          900: "#111118",
          800: "#1a1a2e",
          700: "#22223a",
        },
        // Неоновые акценты.
        neon: {
          cyan: "#00e5ff",
          violet: "#7c3aed",
          purple: "#8a2eff",
          fuchsia: "#d946ef",
          gold: "#fbbf24",
        },
        // Брендовый (совместимость).
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#00e5ff",
          600: "#00c8d6",
          700: "#0ea5b7",
        },
      },
      boxShadow: {
        "neon-cyan": "0 0 12px rgba(0, 229, 255, 0.5), 0 0 32px rgba(0, 229, 255, 0.18)",
        "neon-cyan-lg": "0 0 20px rgba(0, 229, 255, 0.6), 0 0 60px rgba(0, 229, 255, 0.25)",
        "neon-violet": "0 0 12px rgba(124, 58, 237, 0.5), 0 0 32px rgba(124, 58, 237, 0.18)",
        "neon-violet-lg": "0 0 20px rgba(124, 58, 237, 0.6), 0 0 60px rgba(124, 58, 237, 0.25)",
        "neon-fuchsia": "0 0 12px rgba(217, 70, 239, 0.5), 0 0 32px rgba(217, 70, 239, 0.18)",
        "neon-gold": "0 0 12px rgba(251, 191, 36, 0.5), 0 0 32px rgba(251, 191, 36, 0.18)",
        glass: "0 8px 40px rgba(0, 0, 0, 0.45)",
      },
      backdropBlur: {
        glass: "20px",
        sm: "4px",
      },
      backgroundImage: {
        "neon-gradient": "linear-gradient(90deg, #00e5ff, #7c3aed, #d946ef, #fbbf24)",
        "glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02))",
        "deep-gradient":
          "radial-gradient(circle at 20% 20%, rgba(124,58,237,0.25), transparent 40%), radial-gradient(circle at 80% 0%, rgba(0,229,255,0.20), transparent 40%), radial-gradient(circle at 50% 100%, rgba(217,70,239,0.18), transparent 45%)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        "gradient-shift": {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        "glow-pulse": {
          "0%, 100%": { opacity: "0.6", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.4s ease-out both",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
        "gradient-shift": "gradient-shift 6s ease infinite",
        float: "float 6s ease-in-out infinite",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};