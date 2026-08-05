"""
setup_check.py - Глубокая проверка окружения
Проверяет наличие всех компонентов и устанавливает только недостающее
"""
import os
import sys
import subprocess
import importlib.util
import zipfile
import shutil
from pathlib import Path
import urllib.request
import tempfile

BASE_DIR = Path(__file__).resolve().parent

def check_python_version():
    """Проверяет версию Python"""
    print("\n🐍 [0/6] Проверка версии Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"   ❌ Требуется Python 3.10+, у вас {version.major}.{version.minor}")
        print("   👉 Скачайте Python 3.10+: https://www.python.org/downloads/")
        return False
    
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_and_create_dirs():
    """Создает папки только если их нет"""
    print("\n [1/6] Проверка структуры папок...")
    dirs = [
        "data/input", "data/output", "data/reference_clips",
        "data/music_library", "data/temp", "configs", 
        "assets/fonts", "web_ui/static"
    ]
    
    created = []
    for d in dirs:
        path = BASE_DIR / d
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(d)
    
    if created:
        print(f"   ✅ Создано папок: {len(created)}")
        for d in created[:3]:  # Показываем первые 3
            print(f"      - {d}")
        if len(created) > 3:
            print(f"      ... и еще {len(created) - 3}")
    else:
        print("   ✔️  Все папки уже существуют")
    
    return True

def check_and_install_python_packages():
    """Проверяет и устанавливает Python библиотеки только если их нет"""
    print("\n📦 [2/6] Проверка Python-библиотек...")
    
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        print("   ❌ requirements.txt не найден!")
        return False
    
    # Читаем список пакетов
    packages_to_check = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_name = line.split("==")[0].split(">=")[0]
                packages_to_check.append((pkg_name, line))
    
    # Проверяем каждый пакет
    missing = []
    for pkg_name, full_req in packages_to_check:
        # Маппинг имен импорта
        import_map = {
            "opencv-python-headless": "cv2",
            "yt-dlp": "yt_dlp",
            "faster-whisper": "faster_whisper",
            "pyyaml": "yaml",
            "scenedetect": "scenedetect",
            "aiofiles": "aiofiles",
            "python-multipart": "multipart",
        }
        import_name = import_map.get(pkg_name, pkg_name.replace("-", "_"))
        
        if importlib.util.find_spec(import_name) is None:
            missing.append(full_req)
    
    if missing:
        print(f"   ⚠️  Найдено {len(missing)} отсутствующих пакетов")
        print("   🔄 Устанавливаю только недостающее...")
        
        try:
            # Создаем временный файл только с недостающими пакетами
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_req:
                temp_req.write("\n".join(missing))
                temp_req_path = temp_req.name
            
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", temp_req_path, 
                 "--quiet", "--no-warn-script-location"],
                stdout=subprocess.DEVNULL
            )
            
            os.unlink(temp_req_path)  # Удаляем временный файл
            print("   ✅ Все библиотеки установлены!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Ошибка установки: {e}")
            return False
    else:
        print("   ✅ Все библиотеки уже установлены. Ничего не делаю.")
        return True

def check_ffmpeg():
    """Проверяет FFmpeg. Если нет - скачивает автоматически"""
    print("\n [3/6] Проверка FFmpeg...")
    
    # Проверяем, есть ли локальная установка
    local_ffmpeg = BASE_DIR / "ffmpeg_bin" / "ffmpeg.exe"
    if local_ffmpeg.exists():
        # Добавляем в PATH
        os.environ["PATH"] = str(BASE_DIR / "ffmpeg_bin") + os.pathsep + os.environ["PATH"]
        print(f"   ✅ FFmpeg найден (локальная установка)")
        return True
    
    # Проверяем системный FFmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        version = result.stdout.split("\n")[0]
        print(f"   ✅ FFmpeg найден (системный): {version}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("   ️  FFmpeg не найден. Скачиваю автоматически...")
        
        # Скачиваем FFmpeg
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = BASE_DIR / "ffmpeg_temp.zip"
        extract_dir = BASE_DIR / "ffmpeg_extract"
        
        try:
            print("   📥 Скачиваю FFmpeg (~70 MB)...")
            urllib.request.urlretrieve(ffmpeg_url, zip_path)
            
            print("   📦 Распаковываю...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Находим папку bin
            bin_dir = None
            for root, dirs, files in os.walk(extract_dir):
                if 'ffmpeg.exe' in files:
                    bin_dir = Path(root)
                    break
            
            if bin_dir:
                # Копируем в постоянную папку
                ffmpeg_dest = BASE_DIR / "ffmpeg_bin"
                if ffmpeg_dest.exists():
                    shutil.rmtree(ffmpeg_dest)
                shutil.copytree(bin_dir, ffmpeg_dest)
                
                # Добавляем в PATH для текущей сессии
                os.environ["PATH"] = str(ffmpeg_dest) + os.pathsep + os.environ["PATH"]
                
                print(f"   ✅ FFmpeg установлен в: {ffmpeg_dest}")
                print("   💡 Совет: добавьте в PATH Windows для глобального доступа:")
                print(f"      {ffmpeg_dest}")
                
                # Очищаем временные файлы
                zip_path.unlink()
                shutil.rmtree(extract_dir)
                return True
            else:
                print("   ❌ Не удалось найти ffmpeg.exe в архиве")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка установки FFmpeg: {e}")
            print("   👉 Скачайте вручную: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
            return False

def check_ollama():
    """Проверяет Ollama. Если нет - дает инструкцию"""
    print("\n🤖 [4/6] Проверка Ollama...")
    
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5
        )
        print(f"   ✅ Ollama найдена: {result.stdout.strip()}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("   ❌ Ollama не найдена!")
        print("   ⚠️  Ollama требует ручной установки (это безопасно)")
        print("    Скачайте и установите: https://ollama.com/download")
        print("   После установки запустите этот скрипт снова.")
        return False

def check_and_pull_model():
    """Проверяет модель Qwen 2.5 3B. Если нет - скачивает"""
    print("\n [5/6] Проверка AI-модели (Qwen 2.5 3B)...")
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        
        if "qwen2.5:3b" in result.stdout or "qwen2.5:3b-instruct-q4_K_M" in result.stdout:
            print("   ✅ Модель Qwen 2.5 3B уже загружена")
            return True
        else:
            print("   ⚠️  Модель не найдена. Скачиваю (~2 ГБ)...")
            print("   📥 Это займет 5-10 минут в зависимости от скорости интернета...")
            print("   💡 Прогресс загрузки отображается в консоли Ollama")
            
            result = subprocess.run(
                ["ollama", "pull", "qwen2.5:3b-instruct-q4_K_M"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print("   ✅ Модель успешно загружена!")
                return True
            else:
                print(f"   ❌ Ошибка загрузки модели: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"    Ошибка проверки модели: {e}")
        return False

def check_config():
    """Проверяет наличие config.yaml"""
    print("\n⚙️  [6/6] Проверка конфигурации...")
    
    config_path = BASE_DIR / "configs" / "config.yaml"
    if not config_path.exists():
        print("   ️  config.yaml не найден. Будет создан при первом запуске.")
        return True
    else:
        print("   ✅ config.yaml найден")
        return True

def run_all_checks():
    """Запускает все проверки"""
    print("="*60)
    print(" AI AUTO-EDITOR PRO - ПРОВЕРКА ОКРУЖЕНИЯ")
    print("="*60)
    
    checks = [
        check_python_version,
        check_and_create_dirs,
        check_and_install_python_packages,
        check_ffmpeg,
        check_ollama,
        check_and_pull_model,
        check_config
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Ошибка проверки: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print(" РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Пройдено: {passed}/{total}")
    
    if all(results):
        print("\n🎉 ВСЁ ГОТОВО! Можно запускать run_dashboard.py")
        return True
    else:
        print("\n⚠️  Некоторые проверки не пройдены. Исправьте ошибки выше.")
        return False

if __name__ == "__main__":
    run_all_checks()