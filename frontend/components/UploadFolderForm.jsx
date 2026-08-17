"use client";

import { useState } from "react";
import Button from "./Button";
import api from "@/lib/api";

/**
 * Форма загрузки папки с видео на сервере.
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
        <label className="mb-1 block text-sm font-medium text-slate-300">
          Путь к папке на сервере
        </label>
        <input
          type="text"
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          placeholder="/path/to/videos"
          className="glass w-full rounded-xl border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-neon-cyan focus:outline-none focus:ring-2 focus:ring-neon-cyan/30"
        />
      </div>

      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      {result && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300 shadow-[0_0_12px_rgba(34,197,94,0.15)]">
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