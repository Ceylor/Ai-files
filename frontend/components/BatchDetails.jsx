"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Card from "./Card";
import Button from "./Button";
import StatusBadge from "./StatusBadge";
import api from "@/lib/api";

/**
 * Детали пакетной задачи: прогресс, список видео, кнопка запуска.
 * Автоматически обновляется (polling) во время обработки.
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
      await api.batchProcess(batchId);
      setTimeout(loadData, 500);
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  if (!batchId) return null;
  if (loading)
    return (
      <div className="py-10 text-center text-slate-500 dark:text-slate-400">
        Загрузка деталей...
      </div>
    );

  const percent =
    status && status.total_videos
      ? Math.round((status.processed_videos / status.total_videos) * 100)
      : 0;

  const isRunning = status?.status === "processing";
  const isDone = status?.status === "completed" || status?.status === "error";

  return (
    <Card
      title={`Задача #${batchId}`}
      subtitle={status?.folder_path || ""}
    >
      {error && (
        <p className="mb-3 text-sm text-red-400 dark:text-red-300">{error}</p>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusBadge status={status?.status} />
          <span className="text-sm text-slate-600 dark:text-slate-300">
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
        <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Прогресс</span>
          <span>{percent}%</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-neon-cyan via-neon-violet to-neon-fuchsia shadow-neon-cyan"
            initial={{ width: 0 }}
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Список видео */}
      <div className="mt-5">
        <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          Видео в задаче
        </h3>
        {!results?.videos?.length ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Видео не найдены
          </p>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {results.videos.map((v) => (
              <div
                key={v.id}
                className="glass flex items-center justify-between rounded-xl px-3 py-2 transition-all hover:shadow-neon-cyan"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm text-slate-700 dark:text-slate-200">
                    {v.file_path}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    id: {v.id}
                  </div>
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