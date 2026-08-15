"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [videos, setVideos] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [s, v, t] = await Promise.all([
        api.getStatus(),
        api.getVideos(),
        api.batchList(),
      ]);
      setStatus(s);
      setVideos(v.videos || []);
      setTasks(t.tasks || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const completedCount = videos.filter((v) => v.status === "completed").length;
  const composedCount = videos.filter((v) => v.status === "composed").length;
  const processingTasks = tasks.filter((t) => t.status === "processing").length;

  const stats = [
    { label: "Всего видео", value: videos.length, icon: "🎞️" },
    { label: "Клипов готово", value: completedCount, icon: "✅" },
    { label: "Композиций", value: composedCount, icon: "🎬" },
    { label: "Активных задач", value: processingTasks, icon: "⚙️" },
  ];

  // Последние задачи.
  const recentTasks = [...tasks].slice(0, 5);

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Дашборд</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            AI AutoClip Pro 2.0 — статистика и состояние системы
          </p>
        </div>
        <button
          onClick={loadData}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          🔄 Обновить
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-300">
          Ошибка загрузки данных: {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-slate-500 dark:text-slate-400">Загрузка...</div>
      ) : (
        <>
          {/* Карточки статистики */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s) => (
              <Card key={s.label} className="flex items-center gap-4">
                <div className="text-3xl">{s.icon}</div>
                <div>
                  <div className="text-2xl font-bold text-slate-800 dark:text-white">{s.value}</div>
                  <div className="text-sm text-slate-500 dark:text-slate-400">{s.label}</div>
                </div>
              </Card>
            ))}
          </div>

          {/* Последние задачи */}
          <div className="mt-6">
            <Card title="Последние задачи">
              {recentTasks.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Задач пока нет. Создайте обработку через раздел «Задачи».
                </p>
              ) : (
                <div className="space-y-2">
                  {recentTasks.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 dark:border-slate-700"
                    >
                      <div>
                        <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                          #{t.id} — {t.folder_path || "без пути"}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          {t.processed_videos}/{t.total_videos} обработано
                        </div>
                      </div>
                      <StatusBadge status={t.status} />
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </Layout>
  );
}