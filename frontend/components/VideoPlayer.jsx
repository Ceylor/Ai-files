"use client";

/**
 * Встроенный видео-плеер для предпросмотра клипов.
 * Путь к файлу передаётся как src (через прокси Next.js на бэкенд).
 */
export default function VideoPlayer({ src, title }) {
  if (!src) return null;
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-black dark:border-slate-700">
      <video
        src={src}
        controls
        preload="metadata"
        className="mx-auto max-h-[420px] w-full"
      >
        Ваш браузер не поддерживает видео.
      </video>
      {title && (
        <div className="border-t border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200">
          {title}
        </div>
      )}
    </div>
  );
}