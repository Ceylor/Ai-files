"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import VideoPlayer from "@/components/VideoPlayer";
import Timeline from "@/components/Timeline";
import api from "@/lib/api";

/**
 * Строит сегменты таймлайна из метаданных клипа (analysis/extra_metadata).
 * Каждый сегмент — это временной отрезок со своим статусом/эмоцией.
 */
function buildSegments(video) {
  const meta = video.analysis_results || video.extra_metadata || {};
  const scenes = meta.scenes || meta.scene_analysis || [];

  if (!scenes.length) {
    // Fallback: один сегмент на весь клип (длительность берём из метаданных).
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
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Результаты</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Созданные клипы и композиции с визуальным таймлайном
          </p>
        </div>
        <button
          onClick={loadVideos}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          🔄 Обновить
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-300">
          Ошибка: {error}
        </div>
      )}

      <div className="mb-4 flex gap-2">
        {[
          { value: "all", label: "Все" },
          { value: "completed", label: "Клипы" },
          { value: "composed", label: "Композиции" },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
              filter === f.value
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-500 dark:text-slate-400">Загрузка...</div>
      ) : filtered.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Клипов пока нет. Обработайте задачу — результаты появятся здесь.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filtered.map((v) => (
            <Card key={v.id}>
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
                <Timeline segments={buildSegments(v)} />
              </div>

              <div className="mt-3 flex gap-2">
                <a
                  href={srcFor(v)}
                  download
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  ⬇️ Скачать
                </a>
                <button
                  onClick={() => setSelected(v)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  Анализ
                </button>
              </div>

              {selected?.id === v.id && (
                <div className="mt-3 rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-700">
                  <pre className="whitespace-pre-wrap text-slate-600 dark:text-slate-300">
                    {JSON.stringify(v.analysis_results || v.extra_metadata || {}, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </Layout>
  );
}