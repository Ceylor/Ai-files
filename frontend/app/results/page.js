"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import VideoPlayer from "@/components/VideoPlayer";
import Timeline from "@/components/Timeline";
import api from "@/lib/api";

/**
 * Строит сегменты таймлайна из метаданных клипа.
 */
function buildSegments(video) {
  const meta = video.analysis_results || video.extra_metadata || {};
  const scenes = meta.scenes || meta.scene_analysis || [];

  if (!scenes.length) {
    const duration = meta.duration || meta.estimated_duration || 60;
    return [
      {
        id: video.id,
        label: video.file_path.split("/").pop(),
        start: 0,
        end: duration,
        status: video.status,
      },
    ];
  }

  return scenes.map((sc, i) => ({
    id: `${video.id}-${i}`,
    label: sc.label || sc.emotion || sc.role || `сцена ${i + 1}`,
    start: sc.start ?? i * 2,
    end: sc.end ?? sc.start + 2,
    status: sc.status || video.status,
  }));
}

/**
 * Строит точки переходов из метаданных (если есть).
 */
function buildTransitions(video) {
  const meta = video.analysis_results || video.extra_metadata || {};
  const list = meta.transitions || meta.transition_points || [];
  if (!list.length) return [];
  return list.map((t) => ({
    at: t.at ?? t.time ?? 0,
    type: t.type || "cut",
  }));
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function ResultsPage() {
  const [videos, setVideos] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  const filesBase = process.env.NEXT_PUBLIC_FILES_URL || "";

  useEffect(() => {
    loadVideos();
  }, []);

  async function loadVideos() {
    setLoading(true);
    setError("");
    try {
      const res = await api.getVideos();
      setVideos(res.videos || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const clips = videos.filter(
    (v) => v.status === "completed" || v.status === "composed"
  );
  const filtered = filter === "all" ? clips : clips.filter((v) => v.status === filter);

  function srcFor(v) {
    return `${filesBase}${v.file_path}`;
  }

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item} className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold text-slate-800 dark:text-white">
              Результаты
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Созданные клипы и композиции с визуальным таймлайном
            </p>
          </div>
          <button
            onClick={loadVideos}
            className="glass rounded-xl px-4 py-2 text-sm text-slate-600 transition-all hover:shadow-neon-cyan dark:text-slate-300"
          >
            🔄 Обновить
          </button>
        </motion.div>

        {error && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              Ошибка: {error}
            </div>
          </motion.div>
        )}

        <motion.div variants={item} className="mb-4 flex gap-2">
          {[
            { value: "all", label: "Все" },
            { value: "completed", label: "Клипы" },
            { value: "composed", label: "Композиции" },
          ].map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
                filter === f.value
                  ? "bg-gradient-to-r from-neon-cyan to-neon-violet text-white shadow-neon-cyan"
                  : "glass text-slate-600 hover:shadow-neon-cyan dark:text-slate-300"
              }`}
            >
              {f.label}
            </button>
          ))}
        </motion.div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <span className="animate-pulse-soft text-slate-400">Загрузка...</span>
          </div>
        ) : filtered.length === 0 ? (
          <Card>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Клипов пока нет. Обработайте задачу — результаты появятся здесь.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {filtered.map((v) => (
              <motion.div key={v.id} variants={item}>
                <Card>
                  <div className="mb-3 flex items-start justify-between">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">
                        {v.file_path.split("/").pop()}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        id: {v.id}
                      </div>
                    </div>
                    <StatusBadge status={v.status} />
                  </div>

                  <VideoPlayer src={srcFor(v)} title={v.file_path.split("/").pop()} />

                  {/* Визуальный таймлайн */}
                  <div className="mt-3">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Таймлайн
                    </div>
                    <Timeline
                      segments={buildSegments(v)}
                      transitions={buildTransitions(v)}
                    />
                  </div>

                  <div className="mt-3 flex gap-2">
                    <a
                      href={srcFor(v)}
                      download
                      className="btn-neon text-sm"
                    >
                      ⬇️ Скачать
                    </a>
                    <button
                      onClick={() => setSelected(v)}
                      className="glass rounded-xl px-4 py-2 text-sm text-slate-600 transition-all hover:shadow-neon-cyan dark:text-slate-300"
                    >
                      Анализ
                    </button>
                  </div>

                  {selected?.id === v.id && (
                    <div className="glass mt-3 rounded-xl p-3 text-xs">
                      <pre className="whitespace-pre-wrap text-slate-600 dark:text-slate-300">
                        {JSON.stringify(
                          v.analysis_results || v.extra_metadata || {},
                          null,
                          2
                        )}
                      </pre>
                    </div>
                  )}
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </Layout>
  );
}