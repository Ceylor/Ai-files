"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import AnimatedSection from "@/components/AnimatedSection";
import api from "@/lib/api";

const STATUS_COLORS = {
  pending: "#fbbf24",
  processing: "#00f0ff",
  analyzing: "#6366f1",
  completed: "#22c55e",
  composed: "#d946ef",
  error: "#ef4444",
  analyzed: "#14b8a6",
  uploaded: "#94a3b8",
};

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export default function Dashboard() {
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
      const [v, t] = await Promise.all([api.getVideos(), api.batchList()]);
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
    { label: "Всего видео", value: videos.length, icon: "🎞️", accent: "text-neon-cyan" },
    { label: "Клипов готово", value: completedCount, icon: "✅", accent: "text-green-400" },
    { label: "Композиций", value: composedCount, icon: "🎬", accent: "text-neon-fuchsia" },
    { label: "Активных задач", value: processingTasks, icon: "⚙️", accent: "text-neon-gold" },
  ];

  // Donut: распределение по статусам.
  const statusCounts = {};
  videos.forEach((v) => {
    statusCounts[v.status] = (statusCounts[v.status] || 0) + 1;
  });
  const donutData = Object.entries(statusCounts).map(([status, value]) => ({
    name: status,
    value,
    color: STATUS_COLORS[status] || "#94a3b8",
  }));

  // Bar: прогресс задач.
  const barData = tasks.slice(0, 8).map((t) => ({
    name: `#${t.id}`,
    progress: t.total_videos
      ? Math.round((t.processed_videos / t.total_videos) * 100)
      : 0,
  }));

  const recentTasks = [...tasks].slice(0, 5);

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="font-display text-3xl font-bold text-slate-800 dark:text-white">
                Дашборд
              </h1>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                AI AutoClip Pro 2.0 — статистика и состояние системы
              </p>
            </div>
            <button
              onClick={loadData}
              className="glass rounded-xl px-4 py-2 text-sm text-slate-600 transition-all hover:shadow-neon-cyan dark:text-slate-300"
            >
              🔄 Обновить
            </button>
          </div>
        </motion.div>

        {error && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              Ошибка загрузки данных: {error}
            </div>
          </motion.div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <span className="animate-pulse-soft text-slate-400">Загрузка...</span>
          </div>
        ) : (
          <>
            {/* Карточки статистики */}
            <motion.div variants={item} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {stats.map((s) => (
                <Card key={s.label} className="flex items-center gap-4">
                  <div className="text-4xl drop-shadow-[0_0_12px_rgba(0,240,255,0.4)]">
                    {s.icon}
                  </div>
                  <div>
                    <div
                      className={`font-display text-3xl font-bold ${s.accent}`}
                    >
                      {s.value}
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      {s.label}
                    </div>
                  </div>
                </Card>
              ))}
            </motion.div>

            {/* Графики (recharts) */}
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <motion.div variants={item}>
                <Card
                  title="Распределение по статусам"
                  subtitle="Количество видео по текущим статусам"
                >
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={donutData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={3}
                          stroke="none"
                        >
                          {donutData.map((d) => (
                            <Cell key={d.name} fill={d.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: "#111118",
                            border: "1px solid rgba(0,240,255,0.3)",
                            borderRadius: "12px",
                          }}
                          formatter={(value, name) => [`${value}`, name]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </motion.div>

              <motion.div variants={item}>
                <Card title="Прогресс задач" subtitle="Процент обработки по последним задачам">
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="name" stroke="#64748b" />
                        <YAxis stroke="#64748b" />
                        <Tooltip
                          contentStyle={{
                            background: "#111118",
                            border: "1px solid rgba(124,58,237,0.3)",
                            borderRadius: "12px",
                          }}
                        />
                        <Bar dataKey="progress" radius={[6, 6, 0, 0]}>
                          {barData.map((_, i) => (
                            <Cell
                              key={i}
                              fill={
                                ["#00f0ff", "#7c3aed", "#d946ef", "#fbbf24"][
                                  i % 4
                                ]
                              }
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </motion.div>
            </div>

            {/* Последние задачи */}
            <div className="mt-6">
              <motion.div variants={item}>
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
                          className="glass flex items-center justify-between rounded-xl px-4 py-3 transition-all hover:shadow-neon-cyan"
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
              </motion.div>
            </div>
          </>
        )}
      </motion.div>
    </Layout>
  );
}