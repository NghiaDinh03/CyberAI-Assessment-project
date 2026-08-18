#!/usr/bin/env bash
# ================================================================
# CyberAI Platform — first-run setup script
# Run on a fresh git clone:  bash scripts/setup.sh
# ================================================================
# What this does:
#   1. Copies .env.example → .env if .env missing
#   2. Generates a secure JWT_SECRET if still default
#   3. Creates required runtime data folders (so volume mounts work)
#   4. Pulls / builds docker images
#   5. Starts the full stack
#   6. Waits for health checks to pass
# ================================================================

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "=========================================="
echo " CyberAI Platform — First-run setup"
echo " Project: $ROOT"
echo "=========================================="

# ---------- 1. .env file ----------
if [ ! -f ".env" ]; then
  echo "[1/6] .env not found — copying from .env.example"
  cp .env.example .env
  echo "      ✓ .env created. Edit CLOUD_API_KEYS before going to production."
else
  echo "[1/6] .env already exists — skipping"
fi

# ---------- 2. Generate JWT_SECRET if still default ----------
if grep -q "JWT_SECRET=change-me-in-production" .env; then
  echo "[2/6] Generating secure JWT_SECRET (32 bytes hex)"
  if command -v python3 >/dev/null 2>&1; then
    NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  elif command -v openssl >/dev/null 2>&1; then
    NEW_SECRET=$(openssl rand -hex 32)
  else
    echo "      ! python3 / openssl not found — leaving default JWT_SECRET (DEV ONLY)"
    NEW_SECRET=""
  fi
  if [ -n "$NEW_SECRET" ]; then
    # Cross-platform sed in-place (mac uses BSD sed, linux uses GNU sed)
    if sed --version >/dev/null 2>&1; then
      sed -i "s|JWT_SECRET=change-me-in-production|JWT_SECRET=${NEW_SECRET}|" .env
    else
      sed -i '' "s|JWT_SECRET=change-me-in-production|JWT_SECRET=${NEW_SECRET}|" .env
    fi
    echo "      ✓ JWT_SECRET set"
  fi
else
  echo "[2/6] JWT_SECRET already custom — skipping"
fi

# ---------- 3. Create runtime folders ----------
echo "[3/6] Creating runtime data folders"
mkdir -p \
  data/sessions \
  data/uploads \
  data/exports \
  data/evidence \
  data/assessments \
  data/standards \
  data/knowledge_base \
  data/iso_documents \
  data/vector_store \
  data/translations \
  data/models/huggingface \
  models/llm
# .gitkeep so empty folders survive git
for d in sessions uploads exports evidence assessments standards; do
  [ -f "data/$d/.gitkeep" ] || touch "data/$d/.gitkeep"
done
echo "      ✓ Folders ready"

# ---------- 4. Check docker / docker compose ----------
echo "[4/6] Checking Docker availability"
if ! command -v docker >/dev/null 2>&1; then
  echo "      ✗ Docker not installed. Install: https://docs.docker.com/get-docker/"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "      ✗ Docker Compose v2 not available. Update Docker Desktop or install plugin."
  exit 1
fi
echo "      ✓ Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ---------- 5. Build & start ----------
echo "[5/6] Building & starting containers (this may take 5-10 min on first run)"
docker compose up -d --build

# ---------- 6. Wait for health ----------
echo "[6/6] Waiting for backend to become healthy..."
for i in {1..60}; do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    echo "      ✓ Backend healthy after ${i}0s"
    break
  fi
  printf "."
  sleep 10
done
echo

# ---------- Summary ----------
echo "=========================================="
echo " ✓ Setup complete!"
echo "=========================================="
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  Ollama:    http://localhost:11434"
echo "  LocalAI:   http://localhost:8080"
echo
echo " Logs:    docker compose logs -f backend"
echo " Status:  docker compose ps"
echo " Stop:    docker compose down"
echo "=========================================="
echo
echo " Note: Local models (Gemma 4 / Llama 3.1) auto-download on first start."
echo "       Gemma 4 (~9.6 GB) takes ~10 min on a typical broadband connection."
echo "       The chatbot works immediately via cloud (Open Claude) while models pull."
