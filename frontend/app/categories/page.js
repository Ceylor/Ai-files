"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import Button from "@/components/Button";
import api from "@/lib/api";

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Форма создания.
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

  return (
    <Layout>
      <h1 className="mb-6 text-2xl font-bold text-slate-800 dark:text-white">Категории</h1>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Форма создания */}
      <Card title="Новая категория">
        <form onSubmit={handleCreate} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Название
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Путешествия"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Описание
            </label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Описание (необязательно)"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Родительская категория
            </label>
            <select
              value={parentId}
              onChange={(e) => setParentId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            >
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

      {/* Список категорий */}
      <Card className="mt-6" title="Список категорий">
        {loading ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400">Загрузка...</div>
        ) : categories.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Категорий нет</p>
        ) : (
          <div className="space-y-2">
            {categories.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 dark:border-slate-700"
              >
                <div>
                  <div className="font-medium text-slate-700 dark:text-slate-200">{c.name}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
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
    </Layout>
  );
}