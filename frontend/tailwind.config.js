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
        // Тёмный фон.
        night: {
          950: "#0a0a0f",
          900: "#111118",
          800: "#1a1a2e",
        },
        // Неоновые акценты.
        neon: {
          cyan: "#00f0ff",
          violet: "#7c3aed",
          fuchsia: "#d946ef",
          gold: "#fbbf24",
        },
        // Брендовый (совместимость с прошлым).
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#00f0ff",
          600: "#00c8d6",
          700: "#0ea5b7",
        },
      },
      boxShadow: {
        "neon-cyan": "0 0 12px rgba(0, 240, 255, 0.45), 0 0 32px rgba(0, 240, 255, 0.15)",
        "neon-violet": "0 0 12px rgba(124, 58, 237, 0.45), 0 0 32px rgba(124, 58, 237, 0.15)",
        glass: "0 8px 32px rgba(0, 0, 0, 0.35)",
      },
      backdropBlur: {
        glass: "12px",
      },
      backgroundImage: {
        "neon-gradient":
          "linear-gradient(90deg, #00f0ff, #7c3aed, #d946ef, #fbbf24)",
        "glass-gradient":
          "linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        "gradient-shift": {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.4s ease-out both",
        "fade-in": "fade-in 0.3s ease-out both",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
        "gradient-shift": "gradient-shift 6s ease infinite",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};