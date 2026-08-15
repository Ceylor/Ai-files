"use client";

/**
 * Мини-столбчатая диаграмма на чистом SVG (без внешних зависимостей).
 *
 * Props:
 * - data: [{ label, value }]
 * - height: высота графика (px), по умолчанию 160.
 * - color: цвет столбцов (hex), по умолчанию brand-500.
 */
export default function MiniBarChart({ data = [], height = 160, color = "#3b82f6" }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center text-sm text-slate-400" style={{ height }}>
        Нет данных для графика
      </div>
    );
  }

  const max = Math.max(...data.map((d) => d.value), 1);
  const barGap = 8;
  const chartHeight = height - 24; // запас под подписи
  const barWidth = Math.max((100 - (data.length - 1) * barGap) / data.length, 6);

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        className="h-auto w-full"
        role="img"
        aria-label="Столбчатая диаграмма"
      >
        {data.map((d, i) => {
          const barH = (d.value / max) * chartHeight;
          const x = i * (barWidth + barGap);
          const y = height - barH - 18;
          return (
            <g key={d.label ?? i}>
              <title>{`${d.label}: ${d.value}`}</title>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barH}
                rx="2"
                fill={color}
                className="transition-all duration-300"
              />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[11px] text-slate-400 dark:text-slate-500">
        {data.map((d, i) => (
          <span key={d.label ?? i} className="truncate">
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}