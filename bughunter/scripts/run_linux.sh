#!/usr/bin/env bash
# ==============================================================================
# BugHunter AI — Linux Runtime Launcher (Kali Linux / VirtualBox / Ubuntu)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# Ensure user-local Go and pipx bins are in PATH
export GOPATH="${GOPATH:-$HOME/go}"
export PATH="$GOPATH/bin:$HOME/.local/bin:/usr/local/go/bin:$PATH"

echo "================================================================"
echo "           BugHunter AI — Starting on Linux Platform            "
echo "================================================================"

# Get VM IP Address
VM_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

# 1. Setup Backend Virtual Environment
# Robust check: if backend/.venv is missing or from Windows (lacks bin/python), recreate cleanly
if [ ! -x "backend/.venv/bin/python" ]; then
    echo "[*] Creating native Linux Python virtual environment in backend/.venv..."
    rm -rf backend/.venv
    python3 -m venv backend/.venv
    backend/.venv/bin/pip install --upgrade pip --quiet
    echo "[*] Installing backend requirements..."
    backend/.venv/bin/pip install -r backend/requirements.txt --quiet
else
    # Verify core dependencies are actually installed and functional
    if ! backend/.venv/bin/python -c "import fastapi, sqlalchemy, uvicorn, pydantic" >/dev/null 2>&1; then
        echo "[*] Virtualenv exists but has missing dependencies. Re-installing requirements..."
        backend/.venv/bin/pip install -r backend/requirements.txt --quiet
    fi
fi

# Ensure backend/.env exists (copy from root .env or .env.example if missing)
if [ ! -f "backend/.env" ]; then
    if [ -f ".env" ]; then
        echo "[*] Synchronizing root .env to backend/.env..."
        cp .env backend/.env
    elif [ -f "../.env" ]; then
        echo "[*] Synchronizing parent .env to backend/.env..."
        cp ../.env backend/.env
    elif [ -f "backend/.env.example" ]; then
        echo "[*] Creating backend/.env from backend/.env.example..."
        cp backend/.env.example backend/.env
    elif [ -f ".env.example" ]; then
        echo "[*] Creating backend/.env from .env.example..."
        cp .env.example backend/.env
    fi
fi

# Load environment variables into shell and ensure SECRET_KEY fallback
if [ -f "backend/.env" ]; then
    set -a
    source backend/.env 2>/dev/null || true
    set +a
elif [ -f ".env" ]; then
    set -a
    source .env 2>/dev/null || true
    set +a
fi
export SECRET_KEY="${SECRET_KEY:-b9f2d1e8c7a6b5e4d3c2b1a0f9e8d7c6b5a4938271605f4e3d2c1b0a9f8e7d6c}"

# If DATABASE_URL is unset or points to Docker host 'db', use local SQLite for standalone host execution
if [ -z "$DATABASE_URL" ] || echo "$DATABASE_URL" | grep -q "@db:"; then
    export DATABASE_URL="sqlite+aiosqlite:///./bughunter.db"
    export SYNC_DATABASE_URL="sqlite:///./bughunter.db"
fi

# Ensure database tables exist
backend/.venv/bin/python -c "import asyncio; from app.core.database import create_all_tables; asyncio.run(create_all_tables())" 2>/dev/null || true

# 2. Trap for clean termination of background processes
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# 3. Start Backend API on 0.0.0.0:8000
echo "[*] Launching Backend API on 0.0.0.0:8000..."
cd "$DIR/backend"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd "$DIR"

# 4. Start Frontend UI on 0.0.0.0:3000
if [ -d "frontend" ]; then
    echo "[*] Launching Frontend UI on 0.0.0.0:3000..."
    cd "$DIR/frontend"
    if [ ! -d "node_modules" ]; then
        echo "[*] Installing frontend dependencies (npm install)..."
        npm install --silent
    fi
    npx vite --host 0.0.0.0 --port 3000 &
    FRONTEND_PID=$!
    cd "$DIR"
fi

echo ""
echo "================================================================"
echo " [+] BugHunter AI is RUNNING!"
echo "----------------------------------------------------------------"
echo " Local Access (inside VM):"
echo "   Dashboard : http://localhost:3000"
echo "   API Docs  : http://localhost:8000/docs"
echo ""
echo " Host Access (from Windows browser if using Bridged/Host-only):"
echo "   Dashboard : http://${VM_IP}:3000"
echo "   API Docs  : http://${VM_IP}:8000/docs"
echo "================================================================"
echo "Press Ctrl+C to stop all services."

# Wait indefinitely
wait

