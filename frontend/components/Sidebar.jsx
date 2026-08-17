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
    items: [{ href: "/settings", label: "Настройки", icon: "⚙️" }],
  },
];

export default function Sidebar({ theme, onToggleTheme }) {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-white/5 bg-night-900/70 backdrop-blur-2xl">
      {/* Логотип */}
      <div className="flex h-16 items-center gap-2 border-b border-white/5 px-5">
        <span className="text-2xl drop-shadow-[0_0_10px_rgba(0,229,255,0.8)]">🎬</span>
        <div>
          <div className="text-neon-gradient font-display text-lg font-bold">
            AI AutoClip
          </div>
          <div className="text-xs text-slate-400">Pro 2.0</div>
        </div>
      </div>

      {/* Навигация по группам */}
      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
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
                        ? "nav-active"
                        : "text-slate-400 hover:text-white hover:translate-x-1"
                    }`}
                  >
                    {/* Иконка с неоновой подсветкой при наведении/активности */}
                    <span
                      className={`text-lg transition-all duration-200 ${
                        active
                          ? "drop-shadow-[0_0_10px_rgba(0,229,255,0.9)]"
                          : "group-hover:drop-shadow-[0_0_8px_rgba(0,229,255,0.6)] group-hover:scale-110"
                      }`}
                    >
                      {item.icon}
                    </span>
                    <span className={active ? "font-semibold text-white" : ""}>
                      {item.label}
                    </span>
                    {/* Светящаяся точка активного пункта */}
                    {active && (
                      <span className="absolute right-3 h-2 w-2 rounded-full bg-neon-cyan shadow-[0_0_12px_rgba(0,229,255,1)] animate-pulse-soft" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Переключатель темы */}
      <div className="border-t border-white/5 p-4">
        <button
          onClick={onToggleTheme}
          className="glass flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm text-slate-300 transition-all hover:shadow-neon-cyan"
        >
          <span className="flex items-center gap-2">
            {theme === "dark" ? "🌙 Тёмная тема" : "☀️ Светлая тема"}
          </span>
          <span
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              theme === "dark"
                ? "bg-gradient-to-r from-neon-cyan to-neon-violet shadow-neon-cyan"
                : "bg-slate-400"
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