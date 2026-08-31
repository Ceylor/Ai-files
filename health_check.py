#!/usr/bin/env python3
"""
Проверка здоровья AI AutoClip Pro (frontend + backend + API).

Скрипт проверяет:
  1. Синтаксис всех Python-модулей src/ (py_compile).
  2. Импорт src.api.main (создание app = FastAPI()) — без NameError и т.п.
  3. Наличие ключевых API-эндпоинтов в main.py:
       - /api/categories
       - /api/batch/upload_files
       - /api/batch/process/{id}
       - /api/batch/download_links
  4. Целостность критичных frontend-файлов (export default, методы api).
  5. [опционально] Запуск uvicorn и smoke-тест эндпоинтов через httpx.
  6. [опционально] Сборка фронтенда (next build).

Запуск:
    python health_check.py                # только статические проверки (1-4)
    python health_check.py --api          # + live smoke-тест API (запуск uvicorn)
    python health_check.py --frontend     # + сборка Next.js (next build)
    python health_check.py --api --frontend  # всё
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8')
import argparse
import py_compile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
FRONTEND = ROOT / "frontend"

# Ключевые эндпоинты, которые должны существовать в бэкенде.
REQUIRED_ENDPOINTS = [
    '"/api/categories"',
    '"/api/batch/upload_folder"',
    '"/api/batch/upload_files"',
    '"/api/batch/download_links"',
    '"/api/batch/process/{folder_id}"',
    '"/api/batch/status/{folder_id}"',
    '"/api/batch/list"',
]

# Критичные frontend-файлы и что они обязаны содержать.
REQUIRED_FRONTEND = [
    ("frontend/components/StatusBadge.jsx", ["export default function StatusBadge"]),
    ("frontend/components/UploadFolderForm.jsx", ["export default function UploadFolderForm", "batchUploadFiles", "batchDownloadLinks"]),
    ("frontend/components/BatchDetails.jsx", ["export default function BatchDetails", "batchProcess"]),
    ("frontend/components/Button.jsx", ["export default function Button"]),
    ("frontend/components/Card.jsx", ["export default function Card"]),
    ("frontend/components/Layout.jsx", ["export default function Layout"]),
    ("frontend/components/Sidebar.jsx", ["export default function Sidebar"]),
    ("frontend/components/BackgroundFX.jsx", ["export default function BackgroundFX"]),
    ("frontend/components/AnimatedSection.jsx", ["export default function AnimatedSection"]),
    ("frontend/app/page.js", ["export default function Dashboard", "StatusBadge"]),
    ("frontend/app/tasks/page.js", ["export default function TasksPage", "UploadFolderForm", "BatchDetails"]),
    ("frontend/app/learning/page.js", ["export default function LearningPage", "const item = {"]),
    ("frontend/lib/api.js", ["export const api = {", "batchUploadFiles", "batchDownloadLinks", "batchProcess", "export default api;"]),
]


def check_python_compile() -> list:
    """Проверяет компиляцию всех .py файлов в src/."""
    errors = []
    for py_file in sorted(SRC.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"[COMPILE] {py_file.relative_to(ROOT)}: {exc}")
    return errors


def check_main_import() -> list:
    """Пытается импортировать src.api.main — проверка создания app."""
    errors = []
    try:
        sys.path.insert(0, str(ROOT))
        # Импорт запускает все декораторы @app и создаёт app = FastAPI().
        import src.api.main  # noqa: F401
        app = src.api.main.app
        if app is None:
            errors.append("[IMPORT] app не определён в src.api.main")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"[IMPORT] src.api.main: {type(exc).__name__}: {exc}")
    return errors


def check_endpoints() -> list:
    """Проверяет наличие ключевых эндпоинтов в работающем app."""
    errors = []
    try:
        sys.path.insert(0, str(ROOT))
        import src.api.main as main_mod  # noqa: F401
        openapi_paths = set(main_mod.app.openapi()["paths"].keys())
    except Exception as exc:  # noqa: BLE001
        return [f"[ENDPOINT] не удалось получить пути app: {exc}"]
    for ep in REQUIRED_ENDPOINTS:
        path = ep.strip('"')
        if path not in openapi_paths:
            errors.append(f"[ENDPOINT] отсутствует: @app... {ep}")
    return errors


def check_frontend() -> list:
    """Проверяет целостность критичных frontend-файлов."""
    errors = []
    for rel_path, needles in REQUIRED_FRONTEND:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"[FRONTEND] файл отсутствует: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"[FRONTEND] {rel_path}: не найдено '{needle}'")
    return errors


def check_api_live(base_url: str) -> list:
    """Smoke-тест API через httpx (если доступен)."""
    errors = []
    try:
        import httpx
    except ImportError:
        return ["[API] httpx не установлен, live-тест пропущен"]

    try:
        with httpx.Client(timeout=10) as client:
            # 1. Статус.
            r = client.get(f"{base_url}/api/status")
            if r.status_code != 200:
                errors.append(f"[API] GET /api/status -> {r.status_code}")
            # 2. Категории.
            r = client.get(f"{base_url}/api/categories")
            if r.status_code != 200:
                errors.append(f"[API] GET /api/categories -> {r.status_code}")
            # 3. Список пакетных задач.
            r = client.get(f"{base_url}/api/batch/list")
            if r.status_code != 200:
                errors.append(f"[API] GET /api/batch/list -> {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"[API] не удалось подключиться к {base_url}: {exc}")
    return errors


def check_frontend_build() -> list:
    """Запускает сборку Next.js (next build) и проверяет exit code."""
    errors = []
    pkg = FRONTEND / "package.json"
    if not pkg.exists():
        return ["[BUILD] frontend/package.json отсутствует"]
    try:
        import subprocess
        print("  ⏳ Запуск next build (может занять время)...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(FRONTEND),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            errors.append(f"[BUILD] next build упал (code={result.returncode})")
            errors.append(f"[BUILD] tail: {result.stdout[-800:]}\n{result.stderr[-800:]}")
        else:
            print("  ✅ next build прошёл успешно")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"[BUILD] next build: {exc}")
    return errors


def run_backend(base_url: str) -> None:
    """Запускает uvicorn в фоне, ждёт готовности, затем останавливает."""
    import subprocess

    print(f"  ⏳ Старт uvicorn на {base_url}...")
    proc = subprocess.Popen(
        ["uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # Ждём готовности сервера (до 20 сек).
        import httpx
        for _ in range(20):
            try:
                with httpx.Client(timeout=2) as c:
                    c.get(f"{base_url}/api/status")
                return  # сервер поднялся
            except Exception:
                time.sleep(1)
        # Если не поднялся — собираем логи.
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            print("  ❌ uvicorn завершился с ошибкой. Логи:")
            print(out[-2000:])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка здоровья проекта")
    parser.add_argument("--api", action="store_true", help="Live smoke-тест API (uvicorn)")
    parser.add_argument("--frontend", action="store_true", help="Сборка Next.js")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Базовый URL бэкенда")
    args = parser.parse_args()

    all_errors: list = []
    sections = [
        ("Компиляция Python-модулей", check_python_compile()),
        ("Импорт src.api.main (app=FastAPI)", check_main_import()),
        ("Наличие API-эндпоинтов", check_endpoints()),
        ("Целостность frontend-файлов", check_frontend()),
    ]

    for name, errs in sections:
        print(f"▶ {name}")
        if errs:
            for e in errs:
                print(f"  ❌ {e}")
            all_errors.extend(errs)
        else:
            print("  ✅ OK")

    if args.api:
        print("▶ Live smoke-тест API")
        run_backend(args.base_url)
        errs = check_api_live(args.base_url)
        for e in errs:
            print(f"  ❌ {e}")
        all_errors.extend(errs)
        if not errs:
            print("  ✅ API-эндпоинты отвечают")

    if args.frontend:
        print("▶ Сборка фронтенда")
        errs = check_frontend_build()
        for e in errs:
            print(f"  ❌ {e}")
        all_errors.extend(errs)

    print("\n" + "=" * 50)
    if all_errors:
        print(f"❌ Обнаружено ошибок: {len(all_errors)}")
        return 1
    print("✅ ВСЁ ИСПРАВНО: бэкенд компилируется, фронтенд цел, API на месте")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())