"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import StatusBadge from "@/components/StatusBadge";
import Button from "@/components/Button";
import UploadFolderForm from "@/components/UploadFolderForm";
import BatchDetails from "@/components/BatchDetails";
import api from "@/lib/api";

const FILTERS = [
  { value: "all", label: "Все" },
  { value: "pending", label: "В очереди" },
  { value: "processing", label: "Обработка" },
  { value: "completed", label: "Готово" },
  { value: "error", label: "Ошибка" },
];

export default function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadTasks();
  }, []);

  async function loadTasks() {
    setLoading(true);
    setError("");
    try {
      const res = await api.batchList();
      setTasks(res.tasks || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const filtered = filter === "all" ? tasks : tasks.filter((t) => t.status === filter);

  return (
    <Layout>
      <h1 className="mb-2 text-neon-gradient font-display text-4xl font-bold">
        Задачи
      </h1>
      <p className="mb-6 max-w-2xl text-sm text-[var(--text-muted)]">
        Создание клипов из исходников: загрузите видео (папка на сервере, файлы
        с ПК или ссылки) и запустите обработку. Каждое видео пройдёт полный
        пайплайн: ingest → анализ → поиск паттернов → сторибилдер → монтаж → экспорт.
      </p>

      <Card title="Загрузка исходников" subtitle="Создать новую пакетную задачу для монтажа клипов">
        <UploadFolderForm onCreated={() => setTimeout(loadTasks, 500)} />
      </Card>

      <Card className="mt-6" title="Список задач">
        {error && <p className="mb-3 text-sm text-red-500 dark:text-red-400">{error}</p>}

        <div className="mb-4 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-all ${
                filter === f.value
                  ? "bg-gradient-to-r from-neon-cyan to-neon-violet text-white shadow-neon-cyan"
                  : "glass text-[var(--text)] hover:shadow-neon-cyan"
              }`}
            >
              {f.label}
            </button>
          ))}
          <button
            onClick={loadTasks}
            className="glass ml-auto rounded-lg px-3 py-1 text-sm text-[var(--text)] transition-all hover:shadow-neon-cyan"
          >
            🔄
          </button>
        </div>

        {loading ? (
          <div className="py-10 text-center text-[var(--text-muted)]">Загрузка...</div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">Задач не найдено</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--line)] text-[var(--text-muted)]">
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Папка</th>
                  <th className="px-3 py-2">Прогресс</th>
                  <th className="px-3 py-2">Статус</th>
                  <th className="px-3 py-2">Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-[var(--line)] transition-colors hover:bg-[var(--panel-hover)]"
                  >
                    <td className="px-3 py-2 font-medium text-[var(--text)]">#{t.id}</td>
                    <td className="px-3 py-2 text-[var(--text-muted)]">{t.folder_path}</td>
                    <td className="px-3 py-2 text-[var(--text-muted)]">
                      {t.processed_videos}/{t.total_videos}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="px-3 py-2">
                      <Button variant="ghost" onClick={() => setSelectedId(t.id)}>
                        Детали →
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedId && (
        <div className="mt-6">
          <BatchDetails batchId={selectedId} />
        </div>
      )}
    </Layout>
  );
}