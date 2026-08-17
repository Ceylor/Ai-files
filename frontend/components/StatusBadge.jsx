const STATUS_STYLES = {
  pending: "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30",
  processing:
    "bg-cyan-100 text-cyan-700 border-cyan-300 dark:bg-cyan-500/15 dark:text-cyan-300 dark:border-cyan-500/30 dark:shadow-[0_0_8px_rgba(0,229,255,0.3)]",
  completed:
    "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/30",
  composed:
    "bg-fuchsia-100 text-fuchsia-700 border-fuchsia-300 dark:bg-fuchsia-500/15 dark:text-fuchsia-300 dark:border-fuchsia-500/30 dark:shadow-[0_0_8px_rgba(217,70,239,0.3)]",
  error: "bg-red-100 text-red-700 border-red-300 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/30",
  analyzed: "bg-teal-100 text-teal-700 border-teal-300 dark:bg-teal-500/15 dark:text-teal-300 dark:border-teal-500/30",
  uploaded: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-500/15 dark:text-slate-300 dark:border-slate-500/30",
  analyzing:
    "bg-violet-100 text-violet-700 border-violet-300 dark:bg-violet-500/15 dark:text-violet-300 dark:border-violet-500/30 dark:shadow-[0_0_8px_rgba(138,46,255,0.3)]",
};

const STATUS_LABELS = {
  pending: "Ожидает",
  processing: "Обрабатывается",
  completed: "Готово",
  composed: "Композиция",
  error: "Ошибка",
  analyzed: "Проанализировано",
  uploaded: "Загружено",
  analyzing: "Анализ",
};