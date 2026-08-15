"use client";

import { useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    maxClipDuration: 55,
    similarityThreshold: 0.75,
    maxClusterSize: 5,
    category: "default",
  });

  const [saved, setSaved] = useState(false);

  function update(field, value) {
    setSettings((s) => ({ ...s, [field]: value }));
    setSaved(false);
  }

  function handleSave(e) {
    e.preventDefault();
    // Настройки пока применяются через бэкенд (конфиг).
    // Здесь сохраняем локально (localStorage) для UI.
    localStorage.setItem("autoclip_settings", JSON.stringify(settings));
    setSaved(true);
  }

  return (
    <Layout>
      <h1 className="mb-6 text-2xl font-bold text-slate-800 dark:text-white">Настройки</h1>

      <Card title="Параметры обработки" subtitle="Применяются к пакетной обработке (mod9)">
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Макс. длительность клипа (сек)
              </label>
              <input
                type="number"
                value={settings.maxClipDuration}
                onChange={(e) => update("maxClipDuration", Number(e.target.value))}
                min={5}
                max={300}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Порог схожести для композиции
              </label>
              <input
                type="number"
                step="0.05"
                value={settings.similarityThreshold}
                onChange={(e) => update("similarityThreshold", Number(e.target.value))}
                min={0}
                max={1}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Макс. фрагментов в кластере
              </label>
              <input
                type="number"
                value={settings.maxClusterSize}
                onChange={(e) => update("maxClusterSize", Number(e.target.value))}
                min={1}
                max={20}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Категория по умолчанию
              </label>
              <input
                type="text"
                value={settings.category}
                onChange={(e) => update("category", e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              💾 Сохранить
            </button>
            {saved && <span className="text-sm text-green-600 dark:text-green-400">Сохранено</span>}
          </div>
        </form>
      </Card>

      <Card className="mt-6" title="О системе">
        <div className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
          <p>🎬 AI AutoClip Pro 2.0 — ИИ-генерация клипов</p>
          <p>🧠 Многослойный анализ контента</p>
          <p>🗂️ Пакетная обработка и композиция</p>
          <p>📊 Next.js + Tailwind CSS интерфейс</p>
        </div>
      </Card>
    </Layout>
  );
}