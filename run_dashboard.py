"""
run_dashboard.py - Единая точка входа
Автоматически проверяет и устанавливает ВСЁ необходимое
Ничего не переустанавливает, если уже есть
"""
import os
import sys
import subprocess
import importlib.util
import zipfile
import shutil
from pathlib import Path
import urllib.request

BASE_DIR = Path(__file__).resolve().parent

def print_header():
    print("="*60)
    print(" AI AUTO-EDITOR PRO - АВТОМАТИЧЕСКАЯ УСТАНОВКА")
    print("="*60)

def check_and_create_dirs():
    """Создает папки только если их нет"""
    print("\n📂 [1/5] Проверка структуры папок...")
    dirs = [
        "data/input", "data/output", "data/reference_clips",
        "data/music_library", "data/temp", "configs", "assets/fonts"
    ]
    for d in dirs:
        path = BASE_DIR / d
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Создана: {d}")
        else:
            print(f"   ✔️  Уже есть: {d}")

def check_and_install_python_packages():
    """Проверяет и устанавливает Python библиотеки (надёжная версия с нормализацией имён)"""
    print("\n📦 [2/5] Проверка Python-библиотек...")
    
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        print("   ❌ requirements.txt не найден!")
        return False
    
    # Читаем список пакетов из requirements.txt
    required_packages = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Извлекаем чистое имя пакета (без версий и extras)
                pkg_name = line.split("==")[0].split(">=")[0].split("<")[0].split("[")[0].strip()
                required_packages.append(pkg_name)
    
    # Получаем список всех установленных пакетов
    try:
        import importlib.metadata
        installed_packages = {
            pkg.metadata["Name"].lower().replace("-", "_").replace(".", "_"): pkg.version
            for pkg in importlib.metadata.distributions()
        }
    except Exception as e:
        print(f"   ️  Ошибка получения списка пакетов: {e}")
        return False
    
    # Проверяем каждый требуемый пакет
    missing = []
    for pkg_name in required_packages:
        # Нормализуем имя для проверки
        normalized_name = pkg_name.lower().replace("-", "_").replace(".", "_")
        
        # Маппинг специальных случаев
        name_mapping = {
            "opencv_python_headless": "cv2",
            "yt_dlp": "yt_dlp",
            "faster_whisper": "faster_whisper",
            "pyyaml": "yaml",
            "scenedetect": "scenedetect",
            "python_multipart": "multipart",
            "aiofiles": "aiofiles",
        }
        
        check_name = name_mapping.get(normalized_name, normalized_name)
        
        # Проверяем наличие пакета
        if check_name not in installed_packages and normalized_name not in installed_packages:
            missing.append(pkg_name)
    
    if missing:
        print(f"   ⚠️  Найдено {len(missing)} отсутствующих пакетов: {', '.join(missing)}")
        print("   🔄 Устанавливаю только недостающее...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", "--no-warn-script-location"] + missing,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("   ✅ Все библиотеки успешно установлены!")
            return True
        except subprocess.CalledProcessError:
            print("   ❌ Ошибка установки")
            return False
    else:
        print("   ✅ Все библиотеки уже установлены. Ничего не делаю.")
        return True

def check_ffmpeg():
    """Проверяет FFmpeg. Если нет - скачивает автоматически"""
    print("\n🎬 [3/5] Проверка FFmpeg...")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        version = result.stdout.split("\n")[0]
        print(f"   ✅ FFmpeg найден: {version}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("   ️  FFmpeg не найден. Скачиваю автоматически...")
        
        # Скачиваем FFmpeg
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = BASE_DIR / "ffmpeg.zip"
        extract_dir = BASE_DIR / "ffmpeg_temp"
        
        try:
            print("   📥 Скачиваю FFmpeg (это займет пару минут)...")
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
                
                # Сохраняем путь в файл для будущих запусков
                path_file = BASE_DIR / ".ffmpeg_path"
                with open(path_file, "w") as f:
                    f.write(str(ffmpeg_dest))
                
                print(f"   ✅ FFmpeg установлен в: {ffmpeg_dest}")
                print("   ️  ВАЖНО: Для постоянного доступа добавьте в PATH Windows:")
                print(f"      {ffmpeg_dest}")
                
                # Очищаем временные файлы
                zip_path.unlink()
                shutil.rmtree(extract_dir)
                return True
            else:
                print("    Не удалось найти ffmpeg.exe в архиве")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка установки FFmpeg: {e}")
            print("    Скачайте вручную: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
            return False

def check_ollama():
    """Проверяет Ollama. Если нет - дает инструкцию"""
    print("\n🤖 [4/5] Проверка Ollama...")
    
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
        print("   👉 Скачайте и установите: https://ollama.com/download")
        print("   После установки запустите этот скрипт снова.")
        return False

def check_and_pull_model():
    """Проверяет наличие подходящих 3B моделей. Если нет - скачивает"""
    print("\n🧠 [5/5] Проверка AI-модели...")
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        
        # Проверяем наличие ЛЮБОЙ из подходящих 3B моделей
        if "qwen2.5-coder:3b" in result.stdout or "qwen2.5:3b" in result.stdout or "llama3.2:3b" in result.stdout:
            print("   ✅ Подходящая 3B модель уже загружена и готова к работе!")
            return True
        else:
            print("   ⚠️  Подходящая модель не найдена. Скачиваю qwen2.5-coder:3b (~2 ГБ)...")
            print("   📥 Это займет 5-10 минут в зависимости от скорости интернета...")
            
            result = subprocess.run(
                ["ollama", "pull", "qwen2.5-coder:3b"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print("   ✅ Модель успешно загружена!")
                return True
            else:
                print(f"   ❌ Ошибка загрузки модели: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"   ❌ Ошибка проверки модели: {e}")
        return False

def generate_default_config():
    """Создает config.yaml только если его нет"""
    config_path = BASE_DIR / "configs" / "config.yaml"
    if not config_path.exists():
        print("\n⚙️  Создаю дефолтный config.yaml...")
        default_config = """
general:
  input_dir: "./data/input"
  output_dir: "./data/output"
  temp_dir: "./data/temp"
  music_library_dir: "./data/music_library"
  resolution: [1080, 1920]
  fps: 30
  video_bitrate: "8M"
  audio_bitrate: "192k"

ai_brain:
  primary_provider: "ollama"
  ollama:
    model: "qwen2.5:3b-instruct-q4_K_M"
    base_url: "http://localhost:11434"
    timeout: 120
    num_gpu: 15

subtitles:
  enabled: true
  font:
    path: "./assets/fonts/Montserrat-Bold.ttf"
    size: 52
    color: "#FFFFFF"
  highlight:
    enabled: true
    color: "#FFD700"
  position:
    x: 540
    y: 1500
    alignment: "center"

music:
  source: "local_library"
  mood_matching: true
  bpm_sync: true
  volume:
    voice_ducking_db: -14
    music_volume_db: -20

editing:
  max_clip_duration: 55
  min_clip_duration: 15
  auto_reframe:
    enabled: true
    tracking: "face"
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(default_config)
        print("   ✅ config.yaml создан")
    else:
        print("\n⚙️  config.yaml уже существует")

def main():
    print_header()

    # Загружаем .env файл с API-ключами (если есть)
    dotenv_path = BASE_DIR / ".env"
    if dotenv_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path)
            print("   🔑 Загружены переменные окружения из .env")
        except ImportError:
            print("   ℹ️  python-dotenv не установлен, переменные окружения не загружены")
    else:
        print("   ℹ️  .env файл не найден. API-ключи (GigaChat, Pixabay) не будут работать.")
        print("      Скопируйте .env.example в .env и заполните ключи.")
    
    # Проверяем и создаем папки
    check_and_create_dirs()
    
    # Проверяем и устанавливаем Python библиотеки
    if not check_and_install_python_packages():
        print("\n❌ Не удалось установить библиотеки. Проверьте интернет.")
        input("\nНажмите Enter для выхода...")
        return
    
    # Проверяем FFmpeg
    if not check_ffmpeg():
        print("\n️  FFmpeg не установлен. Некоторые функции не будут работать.")
        input("\nНажмите Enter для продолжения...")
    
    # Проверяем Ollama
    if not check_ollama():
        print("\n❌ Ollama не установлена. Без неё AI-функции не работают.")
        input("\nНажмите Enter для выхода...")
        return
    
    # Проверяем и скачиваем модель
    if not check_and_pull_model():
        print("\n⚠️  Модель не загружена. AI-функции будут ограничены.")
        input("\nНажмите Enter для продолжения...")
    
    # Создаем конфиг
    generate_default_config()
    
    print("\n" + "="*60)
    print("✅ ВСЁ ГОТОВО! Запускаю Web-Дашборд...")
    print("="*60)
    print("\n🌐 Откройте в браузере: http://127.0.0.1:8000")
    print("⏹️  Для остановки нажмите Ctrl+C\n")
    
    # Запускаем FastAPI сервер
    try:
        import uvicorn
        uvicorn.run(
            "src.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False
        )
    except ImportError:
        print("❌ FastAPI не установлен. Запустите скрипт снова.")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()