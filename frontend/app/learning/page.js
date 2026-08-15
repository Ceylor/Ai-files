"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import Layout from "@/components/Layout";
import Button from "@/components/Button";
import api from "@/lib/api";

export default function LearningPage() {
  const [categories, setCategories] = useState([]);
  const [learningStatus, setLearningStatus] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("default");
  const [training, setTraining] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setError("");
    try {
      const [cats, st] = await Promise.all([
        api.learningCategories(),
        api.learningStatus(),
      ]);
      setCategories(cats.categories || []);
      setLearningStatus(st);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleTrain(e) {
    e.preventDefault();
    setTraining(true);
    setMessage("");
    setError("");
    try {
      const res = await api.learningTrain(selectedCategory);
      setMessage(`Обучение категории "${selectedCategory}" запущено.`);
      // Обновим статус через пару секунд.
      setTimeout(loadData, 2000);
    } catch (e) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  }

  return (
    <Layout>
      <h1 className="mb-6 text-2xl font-bold text-slate-800 dark:text-white">Обучение</h1>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-300">
          {error}
        </div>
      )}
      {message && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/40 dark:text-green-300">
          {message}
        </div>
      )}

      {/* Запуск обучения */}
      <Card title="Запустить обучение" subtitle="Самообучение на референсных клипах категории">
        <form onSubmit={handleTrain} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Категория
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            >
              {categories.length === 0 ? (
                <option value="default">default</option>
              ) : (
                categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))
              )}
            </select>
          </div>
          <Button type="submit" loading={training}>
            🧠 Запустить обучение
          </Button>
        </form>
      </Card>

      {/* Статус обучения */}
      <Card className="mt-6" title="Статус обучения">
        {learningStatus ? (
          <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300">
            {JSON.stringify(learningStatus, null, 2)}
          </pre>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">Данных пока нет</p>
        )}
      </Card>

      {/* Категории */}
      <Card className="mt-6" title="Обученные категории">
        <div className="flex flex-wrap gap-2">
          {categories.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Нет обученных категорий</p>
          ) : (
            categories.map((c) => (
              <span
                key={c}
                className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 dark:bg-brand-900/40 dark:text-brand-300"
              >
                {c}
              </span>
            ))
          )}
        </div>
      </Card>
    </Layout>
  );
}