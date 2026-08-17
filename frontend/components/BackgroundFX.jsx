"use client";

/**
 * Фоновые hi-tech эффекты:
 * - глубокие неоновые орбы (neon-bg);
 * - анимированная неоновая сетка (neon-grid);
 * - восходящие частицы (particles).
 * Чистый CSS, без внешних зависимостей.
 */
export default function BackgroundFX() {
  return (
    <>
      <div className="neon-bg" aria-hidden="true" />
      <div className="neon-grid" aria-hidden="true" />
      <div className="particles" aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <span key={i} className="particle" />
        ))}
      </div>
    </>
  );
}