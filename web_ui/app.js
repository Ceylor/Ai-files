console.log("✅ AI AutoClip Pro - app.js загружен");

document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ DOM полностью загружен, инициализация...");
    connectWebSocket();
    setupDropZones();
    setupButtons();
});

// ==========================================
// 1. WebSocket для живых логов
// ==========================================
let ws;
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
    
    ws.onopen = () => {
        console.log("✅ WebSocket подключен");
        addLog("[SYSTEM] Соединение с сервером установлено", "text-green-400");
    };
    
    ws.onmessage = (event) => {
        let className = "text-gray-300";
        if (event.data.includes("✅")) className = "text-green-400";
        else if (event.data.includes("❌")) className = "text-red-400";
        else if (event.data.includes("⚠️")) className = "text-yellow-400";
        else if (event.data.includes("🧠")) className = "text-cyan-400 font-bold";
        else if (event.data.includes("🎬")) className = "text-purple-400";
        
        addLog(event.data, className);
    };
    
    ws.onclose = () => {
        console.log("⚠️ WebSocket отключен, переподключение через 2 сек...");
        setTimeout(connectWebSocket, 2000);
    };
    
    ws.onerror = (error) => {
        console.error("❌ Ошибка WebSocket:", error);
    };
}

function addLog(message, className = "text-gray-300") {
    const logConsole = document.getElementById("logConsole");
    if (!logConsole) return;
    
    const div = document.createElement("div");
    div.className = className;
    div.textContent = message;
    logConsole.appendChild(div);
    logConsole.scrollTop = logConsole.scrollHeight; // Автопрокрутка вниз
}

// ==========================================
// 2. Настройка Drag & Drop зон
// ==========================================
function setupDropZones() {
    setupSingleDropZone("refDropZone", "refFiles", "refStatus", "ref");
    setupSingleDropZone("inputDropZone", "inputFiles", "inputStatus", "input");
}

function setupSingleDropZone(zoneId, inputId, statusId, type) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const status = document.getElementById(statusId);
    
    if (!zone || !input || !status) {
        console.error(`Не найдены элементы для ${type}:`, zoneId, inputId, statusId);
        return;
    }

    // Клик по зоне открывает выбор файлов
    zone.addEventListener("click", () => input.click());
    
    // Обработка Drag & Drop
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });
    
    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });
    
    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        handleFiles(e.dataTransfer.files, type, status);
    });
    
    // Обработка выбора через диалог
    input.addEventListener("change", (e) => {
        handleFiles(e.target.files, type, status);
    });
}

async function handleFiles(files, type, statusEl) {
    if (!files || files.length === 0) return;
    
    const category = document.getElementById("categorySelect").value;
    const endpoint = type === "ref" ? "/api/upload_references" : "/api/upload_input";
    
    statusEl.textContent = `Загрузка ${files.length} файлов...`;
    statusEl.className = "text-xs text-yellow-400 mt-2 mono";
    
    const formData = new FormData();
    formData.append("category", category);
    for (let file of files) {
        formData.append("files", file);
    }
    
    try {
        const response = await fetch(endpoint, { method: "POST", body: formData });
        const data = await response.json();
        
        if (data.status === "success") {
            statusEl.textContent = `✅ Загружено: ${data.count} файлов`;
            statusEl.className = "text-xs text-green-400 mt-2 mono";
            if (type === "input") {
                document.getElementById("btnStart").disabled = false;
            }
        } else {
            throw new Error(data.message || "Неизвестная ошибка");
        }
    } catch (error) {
        console.error("Upload error:", error);
        statusEl.textContent = "❌ Ошибка загрузки";
        statusEl.className = "text-xs text-red-400 mt-2 mono";
    }
}

// ==========================================
// 3. Настройка кнопок
// ==========================================
function setupButtons() {
    // Кнопка: Скачать по ссылкам
    document.getElementById("btnTrainLinks").addEventListener("click", async () => {
        const category = document.getElementById("categorySelect").value;
        const links = document.getElementById("linkInput").value;
        const statusEl = document.getElementById("refStatus");
        
        if (!links.trim()) {
            alert("Пожалуйста, вставь хотя бы одну ссылку!");
            return;
        }
        
        statusEl.textContent = "📥 Скачивание по ссылкам...";
        statusEl.className = "text-xs text-yellow-400 mt-2 mono";
        
        const formData = new FormData();
        formData.append("category", category);
        formData.append("links", links);
        
        await fetch("/api/train_links", { method: "POST", body: formData });
    });
    
    // Кнопка: Анализировать стиль
    document.getElementById("btnAnalyze").addEventListener("click", async () => {
        const category = document.getElementById("categorySelect").value;
        const autoCleanup = document.getElementById("autoCleanup").checked;
        
        const formData = new FormData();
        formData.append("category", category);
        formData.append("auto_cleanup", autoCleanup.toString());
        
        await fetch("/api/analyze_style", { method: "POST", body: formData });
    });
    
    // Кнопка: Смонтировать
    document.getElementById("btnStart").addEventListener("click", async () => {
        const category = document.getElementById("categorySelect").value;
        
        const formData = new FormData();
        formData.append("category", category);
        
        await fetch("/api/start_pipeline", { method: "POST", body: formData });
    });
    
    // Кнопка: Очистить логи
    document.getElementById("btnClearLogs").addEventListener("click", () => {
        document.getElementById("logConsole").innerHTML = "";
    });
}