#!/usr/bin/env bash
# ==============================================================================
# CyberAI Platform - Automatic Deployment & Management Script for Linux Server
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}    🚀 CyberAI Platform - Automatic Deploy Script     ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Kiểm tra Docker & Docker Compose
echo -e "\n${YELLOW}[1/5] Kiểm tra môi trường Docker & Docker Compose...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker chưa được cài đặt. Vui lòng cài đặt Docker trước khi tiếp tục.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose v2 chưa được cài đặt.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker & Docker Compose đã sẵn sàng.${NC}"

# 2. Chuẩn bị file cấu hình .env
echo -e "\n${YELLOW}[2/5] Kiểm tra file cấu hình môi trường (.env)...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️ Chưa tìm thấy file .env, tạo mặc định từ .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        cat << 'EOF' > .env
MODEL_NAME=gemma4:latest
SECURITY_MODEL_NAME=gemma4:latest
PREFER_LOCAL=true
LOG_LEVEL=INFO
DEBUG=false
EOF
    fi
    echo -e "${GREEN}✓ Đã khởi tạo .env mặc định với MODEL_NAME=gemma4:latest${NC}"
fi

# 3. Kích hoạt và Build Docker Containers
echo -e "\n${YELLOW}[3/5] Tiến hành Build & Kích hoạt Docker Compose...${NC}"
docker compose up -d --build

# 4. Kiểm tra sức khỏe Ollama & Tải Model gemma4:latest
echo -e "\n${YELLOW}[4/5] Kiểm tra Ollama Engine & Tự động tải Model gemma4...${NC}"
echo "Đang đợi Ollama khởi động..."
until docker exec cyberai-ollama ollama list &> /dev/null; do
    echo -n "."
    sleep 2
done
echo ""

MODEL_TO_PULL=${MODEL_NAME:-gemma4:latest}
echo -e "${BLUE}Đang kiểm tra và tải mô hình ${MODEL_TO_PULL} vào container cyberai-ollama...${NC}"
docker exec cyberai-ollama ollama pull ${MODEL_TO_PULL}

# 5. Kiểm tra sức khỏe toàn bộ hệ thống (Healthcheck)
echo -e "\n${YELLOW}[5/5] Kiểm tra sức khỏe các dịch vụ CyberAI...${NC}"

echo -n "Checking Backend (http://localhost:8000/health)... "
for i in {1..30}; do
    if curl -s -f http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo -n "Checking Frontend (http://localhost:3081)... "
for i in {1..30}; do
    if curl -s -f http://localhost:3081 > /dev/null; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}    🎉 DEPLOY HOÀN TẤT - CYBERAI PLATFORM SẴN SÀNG!   ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e " 🌐 Frontend UI/UX : http://localhost:3081"
echo -e " ⚙️ Backend API    : http://localhost:8000/docs"
echo -e " 🧠 Ollama Engine  : http://localhost:11434"
echo -e " 🔍 SearXNG Search : http://localhost:8888"
echo -e "${GREEN}======================================================${NC}"
