#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  AI AutoClip Pro 2.0 - Deploy Script"
echo "============================================================"
echo ""

# ===== Check Python =====
if ! command -v python3 &> /dev/null; then
    echo "[X] Python3 not found. Install Python 3.9+"
    exit 1
fi
echo "[OK] $(python3 --version)"

# ===== Check Node.js =====
if ! command -v node &> /dev/null; then
    echo "[X] Node.js not found. Install Node.js 18+"
    exit 1
fi
echo "[OK] Node $(node --version)"

# ===== Check FFmpeg =====
if ! command -v ffmpeg &> /dev/null; then
    echo "[X] FFmpeg not found. Install: sudo apt install ffmpeg"
    exit 1
fi
echo "[OK] FFmpeg installed"

# ===== Check yt-dlp =====
if ! command -v yt-dlp &> /dev/null; then
    echo "[!] yt-dlp not found. Installing..."
    pip3 install yt-dlp
fi
echo "[OK] yt-dlp installed"

# ===== Create virtual environment =====
if [ ! -d "venv" ]; then
    echo "[1/6] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/6] Virtual environment exists."
fi

# ===== Install Python dependencies =====
echo "[2/6] Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt -q

# ===== Install frontend dependencies =====
echo "[3/6] Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "      Frontend dependencies exist."
fi
cd ..

# ===== Create data directories =====
echo "[4/6] Creating data directories..."
mkdir -p data data/reference_clips data/input data/output data/downloads logs

# ===== Apply database migrations =====
echo "[5/6] Applying database migrations..."
alembic upgrade head

# ===== Run health check =====
echo "[6/6] Running health check..."
python3 health_check.py

echo ""
echo "============================================================"
echo "  Deploy complete!"
echo ""
echo "  To start: ./start_all.sh"
echo "  Or manually:"
echo "    Backend:  source venv/bin/activate && uvicorn src.api.main:app --host 127.0.0.1 --port 8000"
echo "    Frontend: cd frontend && npm run dev"
echo "============================================================"
