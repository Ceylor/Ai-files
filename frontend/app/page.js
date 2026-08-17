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
  processing: "#00e5ff",
  analyzing: "#8a2eff",
  completed: "#22c55e",
  composed: "#d946ef",
  error: "#ef4444",
  analyzed: "#14b8a6",
  uploaded: "#94a3b8",
};

const STAT_CARDS = [
  { key: "total", label: "Всего видео", icon: "🎞️", accent: "text-neon-cyan", glow: "shadow-neon-cyan" },
  { key: "done", label: "Клипов готово", icon: "✅", accent: "text-emerald-400", glow: "shadow-neon-cyan" },
  { key: "composed", label: "Композиций", icon: "🎬", accent: "text-neon-fuchsia", glow: "shadow-neon-fuchsia" },
  { key: "active", label: "Активных задач", icon: "⚙️", accent: "text-neon-gold", glow: "shadow-neon-gold" },
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
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

  const stats = {
    total: videos.length,
    done: completedCount,
    composed: composedCount,
    active: processingTasks,
  };

  const statusCounts = {};
  videos.forEach((v) => {
    statusCounts[v.status] = (statusCounts[v.status] || 0) + 1;
  });
  const donutData = Object.entries(statusCounts).map(([status, value]) => ({
    name: status,
    value,
    color: STATUS_COLORS[status] || "#94a3b8",
  }));

  const barData = tasks.slice(0, 8).map((t) => ({
    name: `#${t.id}`,
    progress: t.total_videos ? Math.round((t.processed_videos / t.total_videos) * 100) : 0,
  }));

  const recentTasks = [...tasks].slice(0, 5);

  const tooltipStyle = {
    background: "rgba(17,17,24,0.95)",
    border: "1px solid rgba(0,229,255,0.3)",
    borderRadius: "12px",
    color: "#fff",
    boxShadow: "0 0 20px rgba(0,229,255,0.15)",
    backdropFilter: "blur(8px)",
  };

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item} className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-neon-gradient font-display text-4xl font-bold">
              Дашборд
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              AI AutoClip Pro 2.0 — статистика и состояние системы
            </p>
          </div>
          <button
            onClick={loadData}
            className="glass rounded-xl px-5 py-2.5 text-sm font-medium text-slate-200 transition-all hover:shadow-neon-cyan hover:-translate-y-0.5"
          >
            🔄 Обновить
          </button>
        </motion.div>

        {error && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              Ошибка загрузки данных: {error}
            </div>
          </motion.div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <span className="animate-pulse-soft text-lg text-neon-cyan">Загрузка...</span>
          </div>
        ) : (
          <>
            {/* Карточки статистики */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {STAT_CARDS.map((s) => (
                <motion.div key={s.key} variants={item}>
                  <Card className={`group flex items-center gap-5 hover:${s.glow} hover:-translate-y-1`}>
                    {/* Иконка в неоновом круге */}
                    <div
                      className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-2xl ${s.glow} bg-white/5 ring-1 ring-white/10 transition-transform duration-300 group-hover:scale-110`}
                    >
                      {s.icon}
                    </div>
                    <div>
                      <div className={`neon-number text-4xl ${s.accent}`}>
                        {stats[s.key]}
                      </div>
                      <div className="mt-1 text-sm text-slate-400">{s.label}</div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>

            {/* Графики (recharts) */}
            <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
              <motion.div variants={item}>
                <Card title="Распределение по статусам" subtitle="Количество видео по текущим статусам">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={donutData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={3}
                          stroke="none"
                        >
                          {donutData.map((d) => (
                            <Cell key={d.name} fill={d.color} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [`${value}`, name]} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </motion.div>

              <motion.div variants={item}>
                <Card title="Прогресс задач" subtitle="Процент обработки по последним задачам">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="name" stroke="#94a3b8" />
                        <YAxis stroke="#94a3b8" />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Bar dataKey="progress" radius={[8, 8, 0, 0]}>
                          {barData.map((_, i) => (
                            <Cell
                              key={i}
                              fill={
                                ["#00e5ff", "#8a2eff", "#d946ef", "#fbbf24"][i % 4]
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
            <div className="mt-8">
              <motion.div variants={item}>
                <Card title="Последние задачи">
                  {recentTasks.length === 0 ? (
                    <p className="text-sm text-slate-400">
                      Задач пока нет. Создайте обработку через раздел «Задачи».
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {recentTasks.map((t) => (
                        <div
                          key={t.id}
                          className="glass flex items-center justify-between rounded-xl px-5 py-3.5 transition-all hover:shadow-neon-cyan hover:-translate-y-0.5"
                        >
                          <div>
                            <div className="font-medium text-slate-100">
                              #{t.id} — {t.folder_path || "без пути"}
                            </div>
                            <div className="text-xs text-slate-400">
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