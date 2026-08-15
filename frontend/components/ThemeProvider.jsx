"use client";

import { createContext, useContext, useEffect, useState } from "react";

/**
 * Глобальный контекст темы.
 *
 * - Тёмная тема по умолчанию.
 * - Читает сохранённый выбор из localStorage при загрузке.
 * - При переключении сразу обновляет DOM (<html class="dark">) и пишет в localStorage.
 */
const ThemeContext = createContext(null);

const THEME_KEY = "theme";

function getInitialTheme() {
  if (typeof window === "undefined") return "dark"; // SSR: по умолчанию тёмная.
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  // Нет сохранённого выбора — по умолчанию тёмная (не зависит от системной).
  return "dark";
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState("dark");

  // При монтировании — читаем сохранённую тему.
  useEffect(() => {
    setTheme(getInitialTheme());
  }, []);

  // Применяем тему к DOM и сохраняем.
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* localStorage может быть недоступен (приватный режим) */
    }
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));
  const setThemeValue = (t) => setTheme(t === "dark" ? "dark" : "light");

  return (
    <ThemeContext.Provider value={{ theme, toggle, setTheme: setThemeValue }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useThemeContext must be used within ThemeProvider");
  }
  return ctx;
}

export default ThemeProvider;