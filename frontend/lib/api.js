/**
 * Клиент для общения с бэкендом FastAPI.
 * Все запросы идут через прокси Next.js (rewrites) — относительные пути /api/*.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return res.json();
}

export const api = {
  // --- статус / дашборд ---
  getStatus: () => request("/api/status"),

  // --- категории ---
  getCategories: () => request("/api/categories"),
  createCategory: (data) =>
    request("/api/categories", {
      method: "POST",
      body: new URLSearchParams(data).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  updateCategory: (id, data) =>
    request(`/api/categories/${id}`, {
      method: "PUT",
      body: new URLSearchParams(data).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  deleteCategory: (id) =>
    request(`/api/categories/${id}`, { method: "DELETE" }),

  // --- видео ---
  getVideos: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/videos${qs ? `?${qs}` : ""}`);
  },

  // --- пакетная обработка ---
  batchUploadFolder: (folderPath) =>
    request("/api/batch/upload_folder", {
      method: "POST",
      body: new URLSearchParams({ folder_path: folderPath }).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  batchUploadFiles: (files) => {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file);
    }
    return request("/api/batch/upload_files", {
      method: "POST",
      body: form,
    });
  },
  batchDownloadLinks: (links) =>
    request("/api/batch/download_links", {
      method: "POST",
      body: new URLSearchParams({ links }).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  batchProcess: (id) =>
    request(`/api/batch/process/${id}`, { method: "POST" }),
  batchStatus: (id) => request(`/api/batch/status/${id}`),
  batchResults: (id) => request(`/api/batch/results/${id}`),
  batchList: () => request("/api/batch/list"),

  // --- анализ ---
  analyzeVideo: (id) => request(`/api/analysis/analyze/${id}`, { method: "POST" }),
  getAnalysis: (id) => request(`/api/analysis/${id}`),

  // --- обучение ---
  learningTrain: (category) =>
    request("/api/learning/train", {
      method: "POST",
      body: new URLSearchParams({ category }).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  learningStatus: () => request("/api/learning/status"),
  learningCategories: () => request("/api/learning/categories"),
};

export default api;