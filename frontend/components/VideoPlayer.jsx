"use client";

/**
 * Встроенный видео-плеер для предпросмотра клипов.
 * Путь к файлу передаётся как src (через прокси Next.js на бэкенд).
 */
export default function VideoPlayer({ src, title }) {
  if (!src) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-black shadow-lg dark:border-white/10">
      <video
        src={src}
        controls
        preload="metadata"
        className="mx-auto max-h-[420px] w-full"
      >
        Ваш браузер не поддерживает видео.
      </video>
      {title && (
        <div className="glass border-t border-slate-200 px-3 py-2 text-sm text-slate-300 dark:border-white/10">
          {title}
        </div>
      )}
    </div>
  );
}