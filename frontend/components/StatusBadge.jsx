const STATUS_STYLES = {
  pending: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  processing:
    "bg-cyan-500/15 text-cyan-300 border-cyan-500/30 shadow-[0_0_8px_rgba(0,240,255,0.2)]",
  completed: "bg-green-500/15 text-green-300 border-green-500/30",
  composed:
    "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30 shadow-[0_0_8px_rgba(217,70,239,0.2)]",
  error: "bg-red-500/15 text-red-300 border-red-500/30",
  analyzed: "bg-teal-500/15 text-teal-300 border-teal-500/30",
  uploaded: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  analyzing:
    "bg-violet-500/15 text-violet-300 border-violet-500/30 shadow-[0_0_8px_rgba(124,58,237,0.2)]",
};

const STATUS_LABELS = {
  pending: "В очереди",
  processing: "Обработка",
  completed: "Готово",
  composed: "Композиция",
  error: "Ошибка",
  analyzed: "Проанализировано",
  uploaded: "Загружено",
  analyzing: "Анализ",
};

export default function StatusBadge({ status }) {
  const style =
    STATUS_STYLES[status] ||
    "bg-slate-500/15 text-slate-300 border-slate-500/30";
  const label = STATUS_LABELS[status] || status;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium backdrop-blur-sm ${style}`}
    >
      {label}
    </span>
  );
}