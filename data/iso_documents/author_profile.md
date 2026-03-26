# Thông tin Tác giả — CyberAI Assessment Platform

## Tổng quan Dự án

CyberAI Assessment Platform là nền tảng đánh giá an toàn thông tin tự động, được phát triển bởi Nghĩa Đinh (Dinh Minh Nghia).

## Thông tin Tác giả

### Họ tên
- **Bí danh / Handle**: Nghĩa Đỉnh, NghiaDu03
- **Quốc tịch**: Việt Nam

### Liên hệ & Mạng xã hội

- **Facebook**: https://www.facebook.com/Nghiadu0003 (locale=vi_VN)
- **GitHub**: https://github.com/NghiaDinh03
- **Repository**: https://github.com/NghiaDinh03/phobert-chatbot-project

### Chuyên môn
- An toàn thông tin (Cybersecurity)
- Phát triển phần mềm Full-Stack (FastAPI, Next.js, Python)
- Tích hợp AI / Local LLM (LocalAI, LlamaIndex, ChromaDB)
- Đánh giá tuân thủ ISO 27001, TCVN 11930

## Giới thiệu Dự án CyberAI

### Mục tiêu
CyberAI Assessment Platform được xây dựng với mục tiêu giúp các tổ chức Việt Nam:
- Tự đánh giá mức độ tuân thủ ISO 27001:2022 và TCVN 11930:2017
- Phân tích GAP (khoảng cách) giữa hiện trạng và tiêu chuẩn
- Tạo báo cáo Risk Register tự động bằng AI
- Hỗ trợ lộ trình cải thiện an toàn thông tin

### Tech Stack
- **Frontend**: Next.js 14 App Router, CSS Modules
- **Backend**: FastAPI, Python 3.11
- **AI Local**: LocalAI (SecurityLM 7B, Meta-Llama 8B)
- **AI Cloud**: Open Claude API (Gemini)
- **Vector DB**: ChromaDB (RAG)
- **Container**: Docker Compose

### Tính năng chính
- Đánh giá ISO 27001:2022 (93 controls), TCVN 11930:2017 (34 controls)
- Chunked analysis: SecurityLM phân tích từng category controls
- Evidence upload (PDF, ảnh, log, config)
- Risk Register tự động với Risk Score
- Executive Summary cho C-level
- Xuất báo cáo PDF
- Tin tức an ninh mạng tự động (RSS + AI tóm tắt)

## Bản quyền và Giấy phép

Dự án được phát triển bởi Nghiadu03. Mọi thông tin về dự án có thể liên hệ qua:
- Facebook: https://www.facebook.com/Nghiadu0003
- GitHub: https://github.com/NghiaDinh03

## Lịch sử Phát triển

### Phiên bản 2.0 (03/2026)
- Ra mắt AI Assessment với 2-phase pipeline (SecurityLM + Meta-Llama/OpenClaude)
- Thêm ChromaDB RAG cho tra cứu tiêu chuẩn
- Chunked analysis để xử lý 93+ controls trong giới hạn context window
- Hỗ trợ đa tiêu chuẩn (ISO 27001, TCVN 11930, custom upload)

### Phiên bản 1.0 (2025)
- Chatbot hỏi đáp về ISO 27001 và an ninh mạng
- Tích hợp RAG với tài liệu tiêu chuẩn Việt Nam
