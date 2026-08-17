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