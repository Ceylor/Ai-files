export default function Card({ title, subtitle, children, className = "" }) {
  return (
    <div
      className={`glass rounded-2xl p-5 transition-all duration-300 hover:shadow-neon-violet hover:-translate-y-1 ${className}`}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h2 className="font-display text-lg font-semibold text-[var(--heading)]">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}