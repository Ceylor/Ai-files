"use client";

import { useState } from "react";

/**
 * Визуальный таймлайн — движок для отображения и выбора сегментов клипа.
 */
const STATUS_COLORS = {
  processing: "bg-blue-500 dark:bg-blue-400",
  analyzing: "bg-indigo-500 dark:bg-indigo-400",
  completed: "bg-green-500 dark:bg-green-400",
  composed: "bg-purple-500 dark:bg-purple-400",
  error: "bg-red-500 dark:bg-red-400",
  pending: "bg-amber-500 dark:bg-amber-400",
};

export default function Timeline({ segments = [], height = 64, onSelect }) {
  const [selected, setSelected] = useState(null);

  if (!segments.length) {
    return (
      <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-400 dark:border-slate-600 dark:bg-slate-800/50">
        Нет сегментов для отображения на таймлайне
      </div>
    );
  }

  const total = Math.max(...segments.map((s) => s.end || s.start || 0), 1);

  function handleSelect(seg) {
    setSelected(seg.id);
    if (onSelect) onSelect(seg);
  }

  return (
    <div className="space-y-2">
      <div
        className="relative w-full overflow-hidden rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-900"
        style={{ height }}
      >
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            className="absolute top-0 h-full w-px bg-slate-300/60 dark:bg-slate-600/40"
            style={{ left: `${i * 10}%` }}
          />
        ))}

        {segments.map((seg) => {
          const left = (seg.start || 0) / total * 100;
          const width = Math.max(((seg.end || seg.start + 1) - (seg.start || 0)) / total * 100, 2);
          const color = STATUS_COLORS[seg.status] || "bg-slate-400 dark:bg-slate-500";
          const isActive = selected === seg.id;

          return (
            <button
              key={seg.id ?? seg.label}
              onClick={() => handleSelect(seg)}
              className={`absolute top-1 bottom-1 rounded-md px-1.5 text-left text-[10px] font-medium text-white shadow-sm transition-all duration-200 ${color} ${
                isActive ? "ring-2 ring-brand-500 z-10 scale-y-105" : "hover:opacity-80"
              }`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${seg.label} (${seg.start?.toFixed(1) ?? 0}–${seg.end?.toFixed(1) ?? ""}s)`}
            >
              <span className="truncate">{seg.label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
        <span>0s</span>
        <span>{total.toFixed(1)}s</span>
      </div>
    </div>
  );
}