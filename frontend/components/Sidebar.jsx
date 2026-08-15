"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_GROUPS = [
  {
    label: "Рабочее пространство",
    items: [
      { href: "/", label: "Дашборд", icon: "📊" },
      { href: "/tasks", label: "Задачи", icon: "🗂️" },
      { href: "/results", label: "Результаты", icon: "🎬" },
    ],
  },
  {
    label: "Контент",
    items: [
      { href: "/categories", label: "Категории", icon: "🏷️" },
      { href: "/learning", label: "Обучение", icon: "🧠" },
    ],
  },
  {
    label: "Система",
    items: [
      { href: "/settings", label: "Настройки", icon: "⚙️" },
    ],
  },
];

export default function Sidebar({ theme, onToggleTheme }) {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      {/* Логотип */}
      <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-5 dark:border-slate-700">
        <span className="text-2xl">🎬</span>
        <div>
          <div className="text-gradient font-bold text-slate-800 dark:text-white">AI AutoClip</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Pro 2.0</div>
        </div>
      </div>

      {/* Навигация по группам */}
      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              {group.label}
            </div>
            <div className="space-y-1">
              {group.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                      active
                        ? "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300"
                        : "text-slate-600 hover:bg-slate-100 hover:pl-4 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                  >
                    {/* Индикатор активного пункта */}
                    {active && (
                      <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r bg-brand-500" />
                    )}
                    <span className="text-lg">{item.icon}</span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Переключатель темы */}
      <div className="border-t border-slate-200 p-4 dark:border-slate-700">
        <button
          onClick={onToggleTheme}
          className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <span>{theme === "dark" ? "🌙 Тёмная тема" : "☀️ Светлая тема"}</span>
          <span
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              theme === "dark" ? "bg-brand-500" : "bg-slate-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                theme === "dark" ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </span>
        </button>
      </div>
    </aside>
  );
}