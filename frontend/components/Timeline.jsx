"use client";

import { useState } from "react";
import { motion } from "framer-motion";

/**
 * Визуальный таймлайн в стиле профессионального видеоредактора.
 *
 * Props:
 * - segments: [{ id, label, start, end, status }]
 * - transitions: [{ at, type }] — точки переходов между сегментами.
 * - height: высота дорожки.
 * - onSelect: (segment) => void
 */
const STATUS_GRADIENT = {
  processing: "from-blue-500 to-cyan-400",
  analyzing: "from-indigo-500 to-violet-500",
  completed: "from-green-500 to-emerald-400",
  composed: "from-fuchsia-500 to-purple-500",
  error: "from-red-500 to-rose-400",
  pending: "from-amber-500 to-yellow-400",
};

const TRANSITION_LABELS = {
  fade: "🌗",
  zoom: "🔍",
  spin: "🌀",
  cut: "✂️",
};

export default function Timeline({
  segments = [],
  transitions = [],
  height = 64,
  onSelect,
}) {
  const [selected, setSelected] = useState(null);

  if (!segments.length) {
    return (
      <div className="glass flex h-24 items-center justify-center rounded-xl text-sm text-slate-400">
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
      {/* Дорожка */}
      <div
        className="relative w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-100/50 dark:border-white/10 dark:bg-night-900/60"
        style={{ height }}
      >
        {/* Сетка */}
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            className="absolute top-0 h-full w-px bg-slate-300/50 dark:bg-white/5"
            style={{ left: `${i * 10}%` }}
          />
        ))}

        {/* Сегменты */}
        {segments.map((seg) => {
          const left = ((seg.start || 0) / total) * 100;
          const width = Math.max(
            ((seg.end || seg.start + 1) - (seg.start || 0)) / total * 100,
            3
          );
          const gradient =
            STATUS_GRADIENT[seg.status] || "from-slate-400 to-slate-500";
          const isActive = selected === seg.id;

          return (
            <motion.button
              key={seg.id ?? seg.label}
              onClick={() => handleSelect(seg)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: isActive ? 1.04 : 1 }}
              transition={{ duration: 0.25 }}
              className={`absolute top-1 bottom-1 rounded-md bg-gradient-to-r ${gradient} px-1.5 text-left text-[10px] font-semibold text-white shadow-lg transition-all duration-200 ${
                isActive
                  ? "z-10 ring-2 ring-neon-cyan shadow-neon-cyan"
                  : "hover:brightness-110"
              }`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${seg.label} (${seg.start?.toFixed(1) ?? 0}–${seg.end?.toFixed(1) ?? ""}s)`}
            >
              <span className="truncate drop-shadow">{seg.label}</span>
            </motion.button>
          );
        })}

        {/* Маркеры переходов */}
        {transitions.map((tr, i) => {
          const left = ((tr.at || 0) / total) * 100;
          return (
            <div
              key={i}
              className="absolute top-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded-full bg-night-900 px-1 text-[10px] shadow-neon-cyan"
              style={{ left: `${left}%` }}
              title={`Переход: ${tr.type}`}
            >
              {TRANSITION_LABELS[tr.type] || "•"}
            </div>
          );
        })}
      </div>

      {/* Шкала времени */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
        <span>0s</span>
        <span>{total.toFixed(1)}s</span>
      </div>
    </div>
  );
}