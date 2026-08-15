export default function Card({ title, subtitle, children, className = "" }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 ${className}`}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{title}</h2>}
          {subtitle && <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}