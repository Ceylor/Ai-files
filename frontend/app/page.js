"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import MiniBarChart from "@/components/MiniBarChart";
import DonutChart from "@/components/DonutChart";
import AnimatedSection from "@/components/AnimatedSection";
import api from "@/lib/api";

const STATUS_COLORS = {
  pending: "#f59e0b",
  processing: "#3b82f6",
  analyzing: "#6366f1",
  completed: "#22c55e",
  composed: "#a855f7",
  error: "#ef4444",
  analyzed: "#14b8a6",
  uploaded: "#64748b",
};

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

  // Данные для графиков.
  // Распределение по статусам (donut).
  const statusCounts = {};
  videos.forEach((v) => {
    statusCounts[v.status] = (statusCounts[v.status] || 0) + 1;
  });
  const donutData = Object.entries(statusCounts).map(([status, value]) => ({
    label: status,
    value,
    color: STATUS_COLORS[status] || "#94a3b8",
  }));

  // Прогресс по задачам (bar chart) — обработанные/всего.
  const barData = tasks.slice(0, 8).map((t) => ({
    label: `#${t.id}`,
    value: t.total_videos ? Math.round((t.processed_videos / t.total_videos) * 100) : 0,
  }));

  const recentTasks = [...tasks].slice(0, 5);

  return (
    <Layout>
      <AnimatedSection>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Дашборд</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              AI AutoClip Pro 2.0 — статистика и состояние системы
            </p>
          </div>
          <button
            onClick={loadData}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            🔄 Обновить
          </button>
        </div>
      </AnimatedSection>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-300">
          Ошибка загрузки данных: {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <span className="animate-pulse-soft text-slate-500 dark:text-slate-400">Загрузка...</span>
        </div>
      ) : (
        <>
          {/* Карточки статистики */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s, i) => (
              <AnimatedSection key={s.label} delay={i * 80}>
                <Card className="flex items-center gap-4">
                  <div className="text-3xl">{s.icon}</div>
                  <div>
                    <div className="text-2xl font-bold text-slate-800 dark:text-white">{s.value}</div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">{s.label}</div>
                  </div>
                </Card>
              </AnimatedSection>
            ))}
          </div>

          {/* Графики */}
          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <AnimatedSection delay={120}>
              <Card title="Распределение по статусам" subtitle="Количество видео по текущим статусам">
                <div className="flex items-center gap-6">
                  <DonutChart data={donutData} />
                  <div className="space-y-1.5">
                    {donutData.map((d) => (
                      <div key={d.label} className="flex items-center gap-2 text-sm">
                        <span
                          className="inline-block h-3 w-3 rounded-sm"
                          style={{ backgroundColor: d.color }}
                        />
                        <span className="capitalize text-slate-600 dark:text-slate-300">{d.label}</span>
                        <span className="text-slate-400 dark:text-slate-500">{d.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </AnimatedSection>

            <AnimatedSection delay={200}>
              <Card title="Прогресс задач" subtitle="Процент обработки по последним задачам">
                <MiniBarChart data={barData} />
              </Card>
            </AnimatedSection>
          </div>

          {/* Последние задачи */}
          <div className="mt-6">
            <AnimatedSection delay={280}>
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
                        className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700/40"
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
            </AnimatedSection>
          </div>
        </>
      )}
    </Layout>
  );
}