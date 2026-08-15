"use client";

import { useState } from "react";
import Button from "./Button";
import api from "@/lib/api";

/**
 * Форма загрузки папки с видео на сервере.
 * Создаёт batch_job через POST /api/batch/upload_folder.
 */
export default function UploadFolderForm({ onCreated }) {
  const [folderPath, setFolderPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!folderPath.trim()) {
      setError("Укажите путь к папке");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.batchUploadFolder(folderPath.trim());
      setResult(res);
      setFolderPath("");
      if (onCreated) onCreated(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Путь к папке на сервере
        </label>
        <input
          type="text"
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          placeholder="/path/to/videos"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
        />
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {result && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/40 dark:text-green-300">
          ✅ Задача #{result.batch_id} создана. Найдено видео: {result.total_videos},
          зарегистрировано: {result.registered}.
        </div>
      )}

      <Button type="submit" loading={loading}>
        📂 Сканировать папку
      </Button>
    </form>
  );
}