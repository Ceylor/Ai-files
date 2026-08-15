"use client";

/**
 * Фоновые hi-tech эффекты: неоновая сетка + анимированные частицы.
 * Чистый CSS, без внешних зависимостей.
 */
export default function BackgroundFX() {
  return (
    <>
      <div className="neon-grid" aria-hidden="true" />
      <div className="particles" aria-hidden="true">
        {Array.from({ length: 10 }).map((_, i) => (
          <span key={i} className="particle" />
        ))}
      </div>
    </>
  );
}