"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Дашборд", icon: "📊" },
  { href: "/tasks", label: "Задачи", icon: "🗂️" },
  { href: "/results", label: "Результаты", icon: "🎬" },
  { href: "/categories", label: "Категории", icon: "🏷️" },
  { href: "/learning", label: "Обучение", icon: "🧠" },
  { href: "/settings", label: "Настройки", icon: "⚙️" },
];

export default function Sidebar({ theme, onToggleTheme }) {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-5 dark:border-slate-700">
        <span className="text-2xl">🎬</span>
        <div>
          <div className="font-bold text-slate-800 dark:text-white">AI AutoClip</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Pro 2.0</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-200 p-4 dark:border-slate-700">
        <button
          onClick={onToggleTheme}
          className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <span>{theme === "dark" ? "🌙 Тёмная тема" : "☀️ Светлая тема"}</span>
          <span>{theme === "dark" ? "Вкл" : "Выкл"}</span>
        </button>
      </div>
    </aside>
  );
}