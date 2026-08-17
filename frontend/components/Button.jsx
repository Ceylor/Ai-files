export default function Button({
  children,
  variant = "primary",
  loading = false,
  className = "",
  ...props
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-60";
  const variants = {
    primary: "btn-neon",
    secondary:
      "glass text-slate-700 hover:shadow-neon-cyan dark:text-slate-200",
    danger:
      "bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-lg hover:shadow-[0_0_20px_rgba(239,68,68,0.4)] hover:brightness-110",
    ghost:
      "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={loading}
      {...props}
    >
      {loading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
      )}
      {children}
    </button>
  );
}