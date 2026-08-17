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
      await api.learningTrain(selectedCategory);
      setMessage(`Обучение категории "${selectedCategory}" запущено.`);
      setTimeout(loadData, 2000);
    } catch (e) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  }

  return (
    <Layout>
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.div variants={item}>
          <h1 className="mb-6 text-neon-gradient font-display text-4xl font-bold">
            Обучение
          </h1>
        </motion.div>

        {error && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              {error}
            </div>
          </motion.div>
        )}
        {message && (
          <motion.div variants={item}>
            <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
              {message}
            </div>
          </motion.div>
        )}

        <motion.div variants={item}>
          <Card title="Запустить обучение" subtitle="Самообучение на референсных клипах категории">
            <form onSubmit={handleTrain} className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">
                  Категория
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="glass w-full rounded-xl border border-white/10 px-3 py-2 text-sm text-white focus:border-neon-cyan focus:outline-none"
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
        </motion.div>

        <motion.div variants={item}>
          <Card className="mt-6" title="Статус обучения">
            {learningStatus ? (
              <pre className="glass whitespace-pre-wrap rounded-xl p-4 text-sm text-slate-300">
                {JSON.stringify(learningStatus, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-slate-400">Данных пока нет</p>
            )}
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className="mt-6" title="Обученные категории">
            <div className="flex flex-wrap gap-2">
              {categories.length === 0 ? (
                <p className="text-sm text-slate-400">Нет обученных категорий</p>
              ) : (
                categories.map((c) => (
                  <span
                    key={c}
                    className="rounded-full border border-neon-violet/30 bg-neon-violet/15 px-3 py-1 text-sm font-medium text-violet-300 shadow-neon-violet"
                  >
                    {c}
                  </span>
                ))
              )}
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </Layout>
  );
}