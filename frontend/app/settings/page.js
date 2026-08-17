"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import Button from "@/components/Button";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

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
    localStorage.setItem("autoclip_settings", JSON.stringify(settings));
    setSaved(true);
  }

  const inputCls =
    "glass w-full rounded-xl border border-[var(--input-border)] px-3 py-2 text-sm text-[var(--text)] focus:border-neon-cyan focus:outline-none focus:ring-2 focus:ring-neon-cyan/30";

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <h1 className="mb-6 text-neon-gradient font-display text-4xl font-bold">
            Настройки
          </h1>
        </motion.div>

        <motion.div variants={item}>
          <Card title="Параметры обработки" subtitle="Применяются к пакетной обработке (mod9)">
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text)]">
                    Макс. длительность клипа (сек)
                  </label>
                  <input
                    type="number"
                    value={settings.maxClipDuration}
                    onChange={(e) => update("maxClipDuration", Number(e.target.value))}
                    min={5}
                    max={300}
                    className={inputCls}
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text)]">
                    Порог схожести для композиции
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    value={settings.similarityThreshold}
                    onChange={(e) => update("similarityThreshold", Number(e.target.value))}
                    min={0}
                    max={1}
                    className={inputCls}
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text)]">
                    Макс. фрагментов в кластере
                  </label>
                  <input
                    type="number"
                    value={settings.maxClusterSize}
                    onChange={(e) => update("maxClusterSize", Number(e.target.value))}
                    min={1}
                    max={20}
                    className={inputCls}
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text)]">
                    Категория по умолчанию
                  </label>
                  <input
                    type="text"
                    value={settings.category}
                    onChange={(e) => update("category", e.target.value)}
                    className={inputCls}
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button type="submit">💾 Сохранить</Button>
                {saved && <span className="text-sm text-emerald-600 dark:text-emerald-400">Сохранено</span>}
              </div>
            </form>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="mt-6" title="О системе">
            <div className="space-y-1 text-sm text-[var(--text-muted)]">
              <p>🎬 AI AutoClip Pro 2.0 — ИИ-генерация клипов</p>
              <p>🧠 Многослойный анализ контента</p>
              <p>🗂️ Пакетная обработка и композиция</p>
              <p>📊 Next.js + Tailwind CSS интерфейс</p>
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </Layout>
  );
}