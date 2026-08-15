export default function Card({ title, subtitle, children, className = "" }) {
  return (
    <div
      className={`glass rounded-2xl p-5 transition-all duration-300 hover:shadow-neon-violet ${className}`}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h2 className="font-display text-lg font-semibold text-slate-800 dark:text-white">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}