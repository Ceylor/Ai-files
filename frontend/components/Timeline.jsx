"use client";

import { useState } from "react";
import { motion } from "framer-motion";

/**
 * Визуальный таймлайн в стиле профессионального видеоредактора.
 * Сегменты с неоновой обводкой, маркеры переходов светящимися точками.
 */
const STATUS_GRADIENT = {
  processing: "from-cyan-500 to-blue-500",
  analyzing: "from-violet-500 to-purple-500",
  completed: "from-emerald-500 to-green-500",
  composed: "from-fuchsia-500 to-purple-600",
  error: "from-red-500 to-rose-500",
  pending: "from-amber-500 to-yellow-500",
};

const STATUS_GLOW = {
  processing: "shadow-[0_0_14px_rgba(0,229,255,0.5)]",
  analyzing: "shadow-[0_0_14px_rgba(138,46,255,0.5)]",
  completed: "shadow-[0_0_14px_rgba(34,197,94,0.5)]",
  composed: "shadow-[0_0_14px_rgba(217,70,239,0.5)]",
  error: "shadow-[0_0_14px_rgba(239,68,68,0.5)]",
  pending: "shadow-[0_0_14px_rgba(251,191,36,0.5)]",
};

const TRANSITION_GLOW = {
  fade: "#00e5ff",
  zoom: "#8a2eff",
  spin: "#d946ef",
  cut: "#fbbf24",
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
  height = 68,
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
        className="relative w-full overflow-hidden rounded-xl border border-white/10 bg-night-900/60 backdrop-blur-lg"
        style={{ height }}
      >
        {/* Сетка */}
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            className="absolute top-0 h-full w-px bg-white/5"
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
          const gradient = STATUS_GRADIENT[seg.status] || "from-slate-500 to-slate-600";
          const glow = STATUS_GLOW[seg.status] || "";
          const isActive = selected === seg.id;

          return (
            <motion.button
              key={seg.id ?? seg.label}
              onClick={() => handleSelect(seg)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: isActive ? 1.05 : 1 }}
              transition={{ duration: 0.3 }}
              className={`absolute top-1 bottom-1 rounded-lg bg-gradient-to-r ${gradient} px-1.5 text-left text-[10px] font-bold text-white ${glow} ring-1 ring-white/10 transition-all duration-200 ${
                isActive ? "z-10 ring-2 ring-neon-cyan scale-y-105" : "hover:brightness-110"
              }`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${seg.label} (${seg.start?.toFixed(1) ?? 0}–${seg.end?.toFixed(1) ?? ""}s)`}
            >
              <span className="truncate drop-shadow">{seg.label}</span>
            </motion.button>
          );
        })}

        {/* Маркеры переходов — светящиеся точки */}
        {transitions.map((tr, i) => {
          const left = ((tr.at || 0) / total) * 100;
          const color = TRANSITION_GLOW[tr.type] || "#00e5ff";
          return (
            <div
              key={i}
              className="absolute top-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded-full bg-night-950 px-1 text-[11px] ring-1 ring-white/20"
              style={{ boxShadow: `0 0 12px ${color}` }}
              title={`Переход: ${tr.type}`}
            >
              {TRANSITION_LABELS[tr.type] || "•"}
            </div>
          );
        })}
      </div>

      {/* Шкала времени */}
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>0s</span>
        <span>{total.toFixed(1)}s</span>
      </div>
    </div>
  );
}