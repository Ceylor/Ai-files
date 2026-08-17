"use client";

import { useRef, useState } from "react";
import Button from "./Button";
import api from "@/lib/api";

/**
 * Форма загрузки исходников для пакетной задачи:
 *  1. Указание пути к папке на сервере;
 *  2. Загрузка файлов с компьютера (input type="file", multiple);
 *  3. Скачивание видео по ссылкам (yt-dlp: YouTube, VK, RuTube и др.).
 */
export default function UploadFolderForm({ onCreated }) {
  const [folderPath, setFolderPath] = useState("");
  const [files, setFiles] = useState([]);
  const [links, setLinks] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  function notify(res) {
    if (onCreated) onCreated(res);
  }

  // --- 1. Путь к папке на сервере ---
  async function handleFolderSubmit(e) {
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
      notify(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // --- 2. Загрузка файлов с ПК ---
  async function handleFilesSubmit(e) {
    e.preventDefault();
    if (!files.length) {
      setError("Выберите файлы для загрузки");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.batchUploadFiles(files);
      setResult(res);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      notify(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // --- 3. Скачивание по ссылкам ---
  async function handleLinksSubmit(e) {
    e.preventDefault();
    const trimmed = links.trim();
    if (!trimmed) {
      setError("Введите хотя бы одну ссылку");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.batchDownloadLinks(trimmed);
      setResult(res);
      setLinks("");
      notify(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    "glass w-full rounded-xl border border-[var(--input-border)] px-3 py-2 text-sm text-[var(--text)] placeholder-[var(--text-muted)] focus:border-neon-cyan focus:outline-none focus:ring-2 focus:ring-neon-cyan/30";

  return (
    <div className="space-y-5">
      {error && <p className="text-sm text-red-500 dark:text-red-400">{error}</p>}

      {result && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-300">
          ✅ Задача #{result.batch_id} создана. Найдено видео: {result.total_videos},
          зарегистрировано: {result.registered}
          {result.files?.length ? `. Файлы: ${result.files.join(", ")}` : ""}.
        </div>
      )}

      {/* --- 1. Папка на сервере --- */}
      <form onSubmit={handleFolderSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-[var(--text)]">
            📁 Путь к папке на сервере
          </label>
          <input
            type="text"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            placeholder="/path/to/videos"
            className={inputCls}
          />
        </div>
        <Button type="submit" loading={loading}>
          📂 Сканировать папку
        </Button>
      </form>

      {/* --- 2. Файлы с ПК --- */}
      <form onSubmit={handleFilesSubmit} className="space-y-3 border-t border-[var(--line)] pt-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-[var(--text)]">
            💻 Загрузка файлов с компьютера
          </label>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="video/*"
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
            className={inputCls}
          />
          {files.length > 0 && (
            <p className="mt-2 text-xs text-[var(--text-muted)]">
              Выбрано файлов: {files.length}
            </p>
          )}
        </div>
        <Button type="submit" loading={loading}>
          ⬆️ Загрузить файлы
        </Button>
      </form>

      {/* --- 3. Скачивание по ссылкам --- */}
      <form onSubmit={handleLinksSubmit} className="space-y-3 border-t border-[var(--line)] pt-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-[var(--text)]">
            🔗 Скачать видео по ссылкам (YouTube, VK, RuTube)
          </label>
          <textarea
            value={links}
            onChange={(e) => setLinks(e.target.value)}
            placeholder={"Вставьте ссылки, каждая с новой строки:\nhttps://youtube.com/watch?v=...\nhttps://vk.com/video...\nhttps://rutube.ru/video/..."}
            rows={4}
            className={`${inputCls} resize-y`}
          />
        </div>
        <Button type="submit" loading={loading}>
          ⬇️ Скачать по ссылкам
        </Button>
      </form>
    </div>
  );
}