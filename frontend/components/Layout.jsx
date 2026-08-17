"use client";

import Sidebar from "./Sidebar";
import BackgroundFX from "./BackgroundFX";
import { useTheme } from "@/lib/useTheme";

export default function Layout({ children }) {
  const { theme, toggle } = useTheme();

  return (
    <div className="relative min-h-screen bg-night-950">
      {/* Фоновые hi-tech эффекты */}
      <BackgroundFX />

      <Sidebar theme={theme} onToggleTheme={toggle} />

      <main className="relative z-10 ml-60 min-h-screen p-6 lg:p-8">
        {children}
      </main>
    </div>
  );
}