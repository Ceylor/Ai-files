"use client";

import { useThemeContext } from "@/components/ThemeProvider";

/**
 * Хук темы — тонкая обёртка над глобальным ThemeContext.
 * Тема сохраняется в localStorage и применяется к <html> автоматически.
 */
export function useTheme() {
  return useThemeContext();
}

export default useTheme;