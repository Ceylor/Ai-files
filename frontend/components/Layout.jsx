"use client";

import Sidebar from "./Sidebar";
import { useTheme } from "@/lib/useTheme";

export default function Layout({ children }) {
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar theme={theme} onToggleTheme={toggle} />
      <main className="ml-60 min-h-screen p-6">{children}</main>
    </div>
  );
}