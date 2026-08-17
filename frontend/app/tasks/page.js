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
      <h1 className="mb-6 text-neon-gradient font-display text-4xl font-bold">
        Задачи
      </h1>

      <Card title="Загрузка папки" subtitle="Создать новую пакетную задачу">
        <UploadFolderForm onCreated={() => setTimeout(loadTasks, 500)} />
      </Card>

      <Card className="mt-6" title="Список задач">
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <div className="mb-4 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-all ${
                filter === f.value
                  ? "bg-gradient-to-r from-neon-cyan to-neon-violet text-white shadow-neon-cyan"
                  : "glass text-slate-300 hover:shadow-neon-cyan"
              }`}
            >
              {f.label}
            </button>
          ))}
          <button
            onClick={loadTasks}
            className="glass ml-auto rounded-lg px-3 py-1 text-sm text-slate-300 transition-all hover:shadow-neon-cyan"
          >
            🔄
          </button>
        </div>

        {loading ? (
          <div className="py-10 text-center text-slate-400">Загрузка...</div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-slate-400">Задач не найдено</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-slate-500">
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
                    className="border-b border-white/5 transition-colors hover:bg-white/5"
                  >
                    <td className="px-3 py-2 font-medium text-slate-200">
                      #{t.id}
                    </td>
                    <td className="px-3 py-2 text-slate-300">
                      {t.folder_path}
                    </td>
                    <td className="px-3 py-2 text-slate-300">
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