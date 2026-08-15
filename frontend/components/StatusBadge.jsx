const STATUS_STYLES = {
  pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
  processing: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
  composed: "bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
  analyzed: "bg-teal-100 text-teal-700 dark:bg-teal-900/50 dark:text-teal-300",
  uploaded: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  analyzing: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300",
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
  const style = STATUS_STYLES[status] || "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
  const label = STATUS_LABELS[status] || status;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}