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

# 1. Setup Backend Virtual Environment if needed
if [ ! -d "backend/.venv" ]; then
    echo "[*] Creating Python virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
    backend/.venv/bin/pip install --upgrade pip --quiet
    echo "[*] Installing backend requirements..."
    backend/.venv/bin/pip install -r backend/requirements.txt --quiet
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

