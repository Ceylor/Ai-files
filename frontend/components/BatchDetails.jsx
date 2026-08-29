"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Card from "./Card";
import Button from "./Button";
import StatusBadge from "./StatusBadge";
import api from "@/lib/api";

/**
 * Детали пакетной задачи: прогресс, список видео, кнопка запуска.
 */
export default function BatchDetails({ batchId }) {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!batchId) return;
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  async function loadData() {
    try {
      const [s, r] = await Promise.all([
        api.batchStatus(batchId),
        api.batchResults(batchId),
      ]);
      setStatus(s);
      setResults(r);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleStart() {
    setStarting(true);
    setError("");
    try {
      let settings = {};
      try {
        const saved = localStorage.getItem('autoclip_settings');
        if (saved) settings = JSON.parse(saved);
      } catch {}
      await api.batchProcess(batchId, settings);
      setTimeout(loadData, 500);
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  if (!batchId) return null;
  if (loading)
    return <div className="py-10 text-center text-[var(--text-muted)]">Загрузка деталей...</div>;

  const percent =
    status && status.total_videos
      ? Math.round((status.processed_videos / status.total_videos) * 100)
      : 0;

  const isRunning = status?.status === "processing";
  const isDone = status?.status === "completed" || status?.status === "error";

  return (
    <Card title={`Задача #${batchId}`} subtitle={status?.folder_path || ""}>
      {error && <p className="mb-3 text-sm text-red-500 dark:text-red-400">{error}</p>}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusBadge status={status?.status} />
          <span className="text-sm text-[var(--text-muted)]">
            {status?.processed_videos ?? 0}/{status?.total_videos ?? 0} обработано
          </span>
        </div>
        {!isRunning && !isDone && (
          <Button onClick={handleStart} loading={starting}>
            ▶️ Запустить обработку
          </Button>
        )}
      </div>

            {/* Прогресс */}
      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs text-[var(--text-muted)]">
          <span>Прогресс</span>
          <span>{percent}%</span>
        </div>
        {isRunning && status?.total_videos > 0 && (
          <div className="mb-1 text-xs text-[var(--text-muted)]">
            {'Осталось примерно '}
            {Math.floor(((status.total_videos - (status.processed_videos || 0)) * 30) / 60) > 0
              ? Math.floor(((status.total_videos - (status.processed_videos || 0)) * 30) / 60) + 'м '
              : ''}
            {Math.round(((status.total_videos - (status.processed_videos || 0)) * 30) % 60)}с
          </div>
        )}
        <div className="h-3 w-full overflow-hidden rounded-full bg-black/5 ring-1 ring-black/10 dark:bg-white/5 dark:ring-white/10">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-neon-cyan via-neon-violet to-neon-fuchsia shadow-neon-cyan"
            initial={{ width: 0 }}
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Список видео */}
      <div className="mt-5">
        <h3 className="mb-2 text-sm font-semibold text-[var(--text)]">Видео в задаче</h3>
        {!results?.videos?.length ? (
          <p className="text-sm text-[var(--text-muted)]">Видео не найдены</p>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {results.videos.map((v) => (
              <div
                key={v.id}
                className="glass flex items-center justify-between rounded-xl px-3 py-2 transition-all hover:shadow-neon-cyan"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm text-[var(--text)]">{v.file_path}</div>
                  <div className="text-xs text-[var(--text-muted)]">id: {v.id}</div>
                </div>
                <StatusBadge status={v.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}