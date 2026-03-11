<div align="center">
  <h1>PhoBERT AI Platform</h1>
  <p>Enterprise RAG, ISO 27001 Assessment & AI News Aggregator</p>
  <p>
    <a href="README_vi.md">🇻🇳 Read in Vietnamese (Đọc bằng Tiếng Việt)</a>
  </p>
</div>

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [AI Models Integration](#ai-models-integration)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [License](#license)

## Overview
PhoBERT AI Platform is a comprehensive, on-premise AI system featuring **ISO 27001:2022 & TCVN 11930** compliance assessment, Retrieval-Augmented Generation (RAG) capabilities, and Automated News Aggregation. Designed to run completely via Docker Compose, the system utilizes a Multi-Tier Fallback architecture to guarantee maximum High Availability (HA).

## System Architecture

The project leverages a modern Client-Server model powered by various AI models distributed across dedicated Docker containers.

### 1. 🖥️ Frontend (Next.js 15)
- **Ultra-fast SPA:** Single Page Application design eliminating page reloads. Includes modular tabs (Analytics, Chat, Form ISO, News).
- **Client-Side Caching:** Built-in caching (React state/ref) for the News module to persistently store tabs without refetching, reducing bandwidth and latency.
- **Smart Audio Control:** A modern audio interface that provides text-to-speech for news summaries directly on articles or via the History Panel.

### 2. ⚙️ Backend (FastAPI - Python)
A high-performance backend processing requests via multi-threading and robust routing:
- **`chat_service.py`:** Manages conversation routing, interacts with LocalAI, and queries the Vector Database.
- **`model_router.py`:** Orchestrates tasks between LocalAI models (e.g., `SecurityLLM` for auditing and `Llama 3.1` for reporting).
- **`summary_service.py`:** The core of the news summarization engine featuring a **3-Tier Fallback & Round-Robin mechanism**:
  1. **Google Gemini Flash (2.5)**: Rotates through multiple API keys. Implements a 60-second cooldown block if Rate Limit (429) is hit.
  2. **OpenRouter**: If all Gemini keys fail, it cascades to the OpenRouter API key pool.
  3. **LocalAI (On-premise)**: Final fallback using local AI if all cloud APIs are unavailable or quotas are exhausted.
- **`news_service.py`:** Fetches RSS feeds from major cybersecurity sources (The Hacker News, Dark Reading, etc.) and manages a 7-day lifecycle cleanup for `articles_history.json`.
- **`translation_service.py`:** Utilizes the `VinAI Translate` model (135M parameters) for direct CPU-based title translation.

### 3. 💾 Data Persistent Storage (`data/` Directory)
Mounted into Docker to safely retain configurations, logic, and databases:
- **`data/iso_documents/`**: Drop your `.md` files here. ChromaDB converts them into a Knowledge Base for the ISO auditing bot.
- **`data/vector_store/`**: Contains the ChromaDB SQLite Vector Database.
- **`data/summaries/`**: Stores JSON Cache for content and the `data/summaries/audio/` directory.
  - **Audio Caching Mechanism:** URLs are hashed (MD5). Edge-TTS converts Vietnamese text to static `hash.mp3` files. Cached audio files persist for 7 days to eliminate redunant TTS API calls and reduce RAM/Disk usage.
- **`data/assessments/`**: Stores historical generated ISO reports.

## Key Features

### 🏠 Dashboard
- Live 4-timezone world clock.
- Quick navigation to core system features.

### 💬 AI Chat (ISO RAG)
- Employs Retrieval-Augmented Generation (RAG). Extracts vectors from `vector_store` and prompts the Local Llama 3.1 model to provide accurate internal data responses.

### 📊 Analytics & Monitoring
- Ultimate dashboard tracking hardware health (CPU, RAM).
- Maps container metrics and AI Model statuses (Idle/Busy).
- Manage ChromaDB (Clear, Reload) and System History seamlessly.

### 📝 ISO Assessment Form
- Rapid 20+ question survey regarding Enterprise Network Infrastructure.
- Automatically generates comprehensive Action Plan reports using Llama 3.1 & SecurityLLM.
- Analyzes gaps for ISO 27001:2022 and TCVN 11930 standards.

### 📰 AI News Aggregator
- 3 main cybersecurity news categories continuously fetched.
- One-click **🔊 Listen** immediately triggers the summarize -> MP3 generation -> play flow (Plays from cache on subsequent listens).
- **7-Day History Sidebar:** Revisit old articles and listen to cached static audio without consuming API tokens.

## AI Models Integration

1. **Llama 3.1 Instruct (8B)** `[LocalAI]`: The versatile "Brain" for writing, labeling, and fallback summarization.
2. **SecurityLLM (7B)** `[LocalAI]`: Cybersecurity expert model for auditing internal networks.
3. **Gemini 2.5 Flash / OpenRouter** `[Cloud API]`: High-speed "Mercenaries" for multithreaded fast summarization.
4. **VinAI Translate (135M)** `[HuggingFace Transformers]`: 100% On-server Vietnamese translator.
5. **all-MiniLM-L6-v2** `[ChromaDB]`: Embeds markdown text into mathematical vectors.
6. **Edge-TTS** `[Microsoft Service]`: Delivers natural, fluent Text-to-Speech output.

## Quick Start

The architecture deployment is highly streamlined via `docker-compose`. All DNS/Network routing issues are pre-configured.

### 1. Clone & Setup Environment
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
cp .env.example .env
```
> ⚠️ **Note:** Open the `.env` file and populate `GEMINI_API_KEYS` and `OPENROUTER_API_KEYS` using a comma-separated format (`key1,key2,key3`). The system automatically handles Round-Robin load balancing!

### 2. Build & Run
```bash
docker-compose up --build -d
```
*This command pulls required images, downloads GGUF models into `/models`, installs libraries, and spins up `phobert-frontend`, `phobert-backend`, and `phobert-localai` configurations.*

### 3. Access
Open your browser and navigate to **http://localhost:3000**

## Documentation
The project includes deep functional and technical documentation inside the `docs/` directory:
- 📖 **[Architecture Details](./docs/architecture.md)**
- 📖 **[API References](./docs/api.md)**
- 📖 **[Deployment Guide](./docs/deployment.md)**
- 📖 **[ChromaDB Implementation](./docs/chromadb_guide.md)**
- 📖 **[RAG & PICO Markdown Formatting Standard](./docs/markdown_rag_standard.md)**

## License
This project is proprietary and built for enterprise network assessment purposes. 
*Focused on premium end-user experiences, data security, memory overflow protection, and multi-tier robust fallback systems.*
