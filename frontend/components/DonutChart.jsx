"use client";

/**
 * Кольцевая (donut) диаграмма на чистом SVG.
 *
 * Props:
 * - data: [{ label, value, color }]
 * - size: диаметр (px), по умолчанию 140.
 * - thickness: толщина кольца (px), по умолчанию 16.
 */
export default function DonutChart({ data = [], size = 140, thickness = 16 }) {
  const total = data.reduce((sum, d) => sum + (d.value || 0), 0);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  if (!total) {
    return (
      <div
        className="flex items-center justify-center text-sm text-slate-400"
        style={{ width: size, height: size }}
      >
        Нет данных
      </div>
    );
  }

  let offset = 0;

  return (
    <svg width={size} height={size} role="img" aria-label="Кольцевая диаграмма">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        className="text-slate-100 dark:text-slate-700"
        strokeWidth={thickness}
      />
      {data.map((d, i) => {
        const frac = (d.value || 0) / total;
        const dash = frac * circumference;
        const segment = (
          <circle
            key={d.label ?? i}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={d.color || "#3b82f6"}
            strokeWidth={thickness}
            strokeDasharray={`${dash} ${circumference - dash}`}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            className="transition-all duration-300"
          >
            <title>{`${d.label}: ${d.value} (${(frac * 100).toFixed(0)}%)`}</title>
          </circle>
        );
        offset += dash;
        return segment;
      })}
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-slate-800 text-lg font-bold dark:fill-white"
      >
        {total}
      </text>
    </svg>
  );
}