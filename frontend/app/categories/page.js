"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import Button from "@/components/Button";
import api from "@/lib/api";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parentId, setParentId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  async function loadCategories() {
    setLoading(true);
    setError("");
    try {
      const res = await api.getCategories();
      setCategories(res.categories || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await api.createCategory({
        name: name.trim(),
        description: description.trim() || null,
        parent_id: parentId ? String(parentId) : null,
      });
      setName("");
      setDescription("");
      setParentId("");
      await loadCategories();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Удалить категорию?")) return;
    setError("");
    try {
      await api.deleteCategory(id);
      await loadCategories();
    } catch (e) {
      setError(e.message);
    }
  }

  const inputCls =
    "glass w-full rounded-xl border border-[var(--input-border)] px-3 py-2 text-sm text-[var(--text)] placeholder-[var(--text-muted)] focus:border-neon-cyan focus:outline-none focus:ring-2 focus:ring-neon-cyan/30";

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <h1 className="mb-6 text-neon-gradient font-display text-4xl font-bold">
            Категории
          </h1>
        </motion.div>

        {error && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-300">
              {error}
            </div>
          </motion.div>
        )}

        <motion.div variants={item}>
          <Card title="Новая категория">
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-[var(--text)]">Название</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Например: Путешествия"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-[var(--text)]">Описание</label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Описание (необязательно)"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-[var(--text)]">
                  Родительская категория
                </label>
                <select value={parentId} onChange={(e) => setParentId(e.target.value)} className={inputCls}>
                  <option value="">— нет —</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <Button type="submit" loading={submitting}>
                ➕ Создать
              </Button>
            </form>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="mt-6" title="Список категорий">
            {loading ? (
              <div className="py-10 text-center text-[var(--text-muted)]">Загрузка...</div>
            ) : categories.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">Категорий нет</p>
            ) : (
              <div className="space-y-2">
                {categories.map((c) => (
                  <div
                    key={c.id}
                    className="glass flex items-center justify-between rounded-xl px-4 py-3 transition-all hover:shadow-neon-cyan"
                  >
                    <div>
                      <div className="font-medium text-[var(--text)]">{c.name}</div>
                      <div className="text-xs text-[var(--text-muted)]">
                        {c.description || "Без описания"}
                        {c.parent_id ? ` • родитель: #${c.parent_id}` : ""}
                      </div>
                    </div>
                    <Button variant="danger" onClick={() => handleDelete(c.id)}>
                      🗑️
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      </motion.div>
    </Layout>
  );
}