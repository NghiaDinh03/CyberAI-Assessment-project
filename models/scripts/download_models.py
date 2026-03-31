#!/usr/bin/env python3
"""
Download GGUF model files for LocalAI.

Usage:
    python scripts/download_models.py

Models downloaded:
  - Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf  (~5GB) — Phase 2 report formatting
  - SecurityLLM-7B-Q4_K_M.gguf              (~4GB) — Phase 1 GAP analysis

Total: ~9GB. Requires 16GB RAM minimum to run both simultaneously.
"""

import os
import sys
import urllib.request

MODELS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LLM_DIR = os.path.join(MODELS_DIR, "llm")

MODELS = [
    {
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size": "~5.0 GB",
        "description": "Meta-Llama 3.1 8B Instruct (Q4_K_M quantized) — Phase 2 report formatting",
    },
    {
        "filename": "SecurityLLM-7B-Q4_K_M.gguf",
        "url": "https://huggingface.co/QuantFactory/SecurityLLM-GGUF/resolve/main/SecurityLLM.Q4_K_M.gguf",
        "size": "~4.1 GB",
        "description": "SecurityLLM 7B (Q4_K_M quantized) — Phase 1 GAP analysis",
    },
]


def download_file(url: str, dest: str, label: str):
    print(f"\n📥 Downloading: {label}")
    print(f"   URL: {url}")
    print(f"   Dest: {dest}")

    def progress(count, block_size, total_size):
        if total_size > 0:
            pct = min(100, count * block_size * 100 // total_size)
            downloaded = count * block_size / (1024 ** 3)
            total = total_size / (1024 ** 3)
            print(f"\r   Progress: {pct}% ({downloaded:.2f}/{total:.2f} GB)", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=progress)
    print(f"\n   ✅ Done: {os.path.getsize(dest) / (1024**3):.2f} GB saved")


def main():
    os.makedirs(LLM_DIR, exist_ok=True)
    print(f"📁 Models directory: {LLM_DIR}")
    print(f"📋 Models to download: {len(MODELS)}")

    for model in MODELS:
        dest_path = os.path.join(LLM_DIR, model["filename"])
        if os.path.exists(dest_path):
            size_gb = os.path.getsize(dest_path) / (1024 ** 3)
            if size_gb > 1.0:
                print(f"\n⏭️  Skipping (already exists): {model['filename']} ({size_gb:.2f} GB)")
                continue
            else:
                print(f"\n⚠️  File exists but too small ({size_gb:.2f} GB) — re-downloading: {model['filename']}")

        try:
            download_file(model["url"], dest_path, model["description"])
        except Exception as e:
            print(f"\n❌ Failed to download {model['filename']}: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            sys.exit(1)

    print("\n\n🎉 All models downloaded successfully!")
    print(f"📁 Location: {LLM_DIR}")
    print("\nNext steps:")
    print("  1. Run: docker-compose up -d localai")
    print("  2. Wait for LocalAI to start (~30s)")
    print("  3. Set PREFER_LOCAL=true in .env")
    print("  4. Restart backend: docker-compose restart backend")


if __name__ == "__main__":
    main()
