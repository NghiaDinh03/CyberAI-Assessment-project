#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download GGUF model files for LocalAI.

Usage:
    python scripts/download_models.py --status
    python scripts/download_models.py --model gemma-3-4b
    python scripts/download_models.py --model gemma-3-12b
    python scripts/download_models.py --model gemma-4-31b-q3   # Q3_K_M, ~14GB
    python scripts/download_models.py --model all

Models dir: models/llm/
Requires:   pip install huggingface_hub hf_transfer
"""

import os
import sys
import argparse
import time

# Force UTF-8 on Windows consoles (cp1252 can't print box-drawing chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# GGUF files live in models/llm/weights/ to prevent LocalAI v4.x from
# scanning them at startup (it reads GGUF metadata per file = 10+ min delay).
# YAMLs reference them as  model: weights/filename.gguf
MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "llm", "weights"
)

# ── Model registry (verified repo_id + filename from HF API) ───────────────
MODELS = {
    # Gemma 3 — public repos (bartowski/google_gemma-3-*-GGUF), no auth needed
    "gemma-3-4b": {
        "filename": "google_gemma-3-4b-it-Q4_K_M.gguf",
        "repo_id": "bartowski/google_gemma-3-4b-it-GGUF",
        "hf_filename": "google_gemma-3-4b-it-Q4_K_M.gguf",
        "size_gb": 2.5,
        "auth": False,
        "description": "Gemma 3 4B Instruct Q4_K_M — fast, ~3GB RAM",
    },
    "gemma-3-12b": {
        "filename": "google_gemma-3-12b-it-Q4_K_M.gguf",
        "repo_id": "bartowski/google_gemma-3-12b-it-GGUF",
        "hf_filename": "google_gemma-3-12b-it-Q4_K_M.gguf",
        "size_gb": 7.3,
        "auth": False,
        "description": "Gemma 3 12B Instruct Q4_K_M — balanced, ~8GB RAM",
    },
    # Gemma 4 — Google's latest (April 2026), public from unsloth, no auth
    "gemma-4-31b": {
        "filename": "gemma-4-31B-it-Q4_K_M.gguf",
        "repo_id": "unsloth/gemma-4-31B-it-GGUF",
        "hf_filename": "gemma-4-31B-it-Q4_K_M.gguf",
        "size_gb": 19.0,
        "auth": False,
        "description": "Gemma 4 31B Instruct Q4_K_M — best quality, ~20GB RAM",
    },
    "gemma-4-31b-q3": {
        "filename": "gemma-4-31B-it-Q3_K_M.gguf",
        "repo_id": "unsloth/gemma-4-31B-it-GGUF",
        "hf_filename": "gemma-4-31B-it-Q3_K_M.gguf",
        "size_gb": 13.5,
        "auth": False,
        "description": "Gemma 4 31B Instruct Q3_K_M — lighter, ~14GB RAM",
    },
    # Existing models (already downloaded)
    "llama": {
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "hf_filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "auth": False,
        "description": "Meta Llama 3.1 8B Instruct Q4_K_M — general LLM, ~5GB RAM",
    },
    "security": {
        "filename": "SecurityLLM-7B-Q4_K_M.gguf",
        "repo_id": "QuantFactory/SecurityLLM-GGUF",
        "hf_filename": "SecurityLLM.Q4_K_M.gguf",
        "size_gb": 4.2,
        "auth": False,
        "description": "SecurityLLM 7B Q4_K_M — cybersecurity domain, ~4.5GB RAM",
    },
}

_HF_TOKEN: str = ""


def progress_bar(downloaded: int, total: int, bar_width: int = 40) -> str:
    if total <= 0:
        return f"  {downloaded // (1024*1024)} MB downloaded"
    pct = downloaded / total
    filled = int(bar_width * pct)
    bar = "#" * filled + "-" * (bar_width - filled)
    mb_done = downloaded // (1024 * 1024)
    mb_total = total // (1024 * 1024)
    return f"  [{bar}] {pct*100:.1f}%  {mb_done}/{mb_total} MB"


def download_direct(url: str, dest_path: str, token: str = "") -> bool:
    """Direct urllib download with progress bar."""
    import urllib.request
    tmp_path = dest_path + ".part"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB
            start = time.time()
            with open(tmp_path, "wb") as f:
                while True:
                    data = response.read(chunk_size)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    elapsed = time.time() - start
                    speed = downloaded / elapsed / (1024 * 1024) if elapsed > 0 else 0
                    print(
                        f"\r{progress_bar(downloaded, total)}  {speed:.1f} MB/s",
                        end="", flush=True
                    )
        print()
        os.rename(tmp_path, dest_path)
        return True
    except Exception as e:
        print(f"\n  [!] Direct download failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def download_via_hf_hub(repo_id: str, hf_filename: str, dest_path: str, token: str = "") -> bool:
    """Use huggingface_hub with optional hf_transfer acceleration."""
    try:
        from huggingface_hub import hf_hub_download, login, whoami
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        if token:
            try:
                login(token=token, add_to_git_credential=False)
                user = whoami(token=token)
                print(f"  Logged in as: {user.get('name', 'unknown')}")
            except Exception as le:
                print(f"  HF login warning: {le}")

        # Enable hf_transfer for multi-threaded fast download
        try:
            import hf_transfer  # noqa: F401
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
            print(f"  hf_transfer: enabled (faster multi-threaded download)")
        except ImportError:
            print(f"  hf_transfer: not installed (pip install hf_transfer for faster downloads)")

        print(f"  Downloading via huggingface_hub...")
        cached = hf_hub_download(
            repo_id=repo_id,
            filename=hf_filename,
            local_dir=MODELS_DIR,
            token=token or None,
        )
        real_cached = os.path.realpath(cached)
        real_dest = os.path.realpath(dest_path)
        if real_cached != real_dest and os.path.exists(cached):
            import shutil
            shutil.move(cached, dest_path)
        return True
    except ImportError:
        print("  huggingface_hub not installed. Run: pip install huggingface_hub")
        return False
    except Exception as e:
        print(f"  huggingface_hub error: {e}")
        return False


def download_model(key: str, info: dict, token: str = "") -> bool:
    dest_path = os.path.join(MODELS_DIR, info["filename"])

    if os.path.exists(dest_path):
        size_mb = os.path.getsize(dest_path) // (1024 * 1024)
        print(f"  [OK] Already exists: {info['filename']} ({size_mb} MB) -- skipping")
        return True

    print(f"\n{'='*65}")
    print(f"  Model   : {key}")
    print(f"  Info    : {info['description']}")
    print(f"  File    : {info['filename']}")
    print(f"  Size    : ~{info['size_gb']:.1f} GB")
    print(f"  Repo    : {info['repo_id']}")
    print(f"  Auth    : {'Required' if info['auth'] else 'Not required (public)'}")
    print(f"{'='*65}")

    os.makedirs(MODELS_DIR, exist_ok=True)

    # Strategy 1: huggingface_hub (preferred)
    if download_via_hf_hub(info["repo_id"], info["hf_filename"], dest_path, token):
        if os.path.exists(dest_path):
            size_mb = os.path.getsize(dest_path) // (1024 * 1024)
            print(f"  [OK] Done: {info['filename']} ({size_mb} MB)")
            return True

    # Strategy 2: Direct CDN URL
    hf_url = f"https://huggingface.co/{info['repo_id']}/resolve/main/{info['hf_filename']}"
    print(f"  Fallback: direct download from {hf_url}")
    if download_direct(hf_url, dest_path, token):
        size_mb = os.path.getsize(dest_path) // (1024 * 1024)
        print(f"  [OK] Done: {info['filename']} ({size_mb} MB)")
        return True

    print(f"\n  [FAIL] Could not download {key}")
    print(f"  Manual: https://huggingface.co/{info['repo_id']}")
    print(f"  Save to: {dest_path}")
    return False


def check_status():
    """Print download status of all models and LocalAI visibility."""
    print("\nModel Status -- models/llm/")
    print("-" * 65)
    all_ok = True
    for key, info in MODELS.items():
        dest = os.path.join(MODELS_DIR, info["filename"])
        if os.path.exists(dest):
            size_mb = os.path.getsize(dest) // (1024 * 1024)
            print(f"  [OK]     {key:<16} {info['filename']:<45} {size_mb:>5} MB")
        else:
            auth_note = " (needs HF token)" if info["auth"] else " (public)"
            print(f"  [MISS]   {key:<16} {info['filename']:<45} ~{info['size_gb']:.0f}GB{auth_note}")
            all_ok = False
    print("-" * 65)

    # Check LocalAI API
    try:
        import urllib.request as ur, json
        with ur.urlopen("http://localhost:8080/v1/models", timeout=5) as r:
            data = json.loads(r.read())
            ids = [m["id"] for m in data.get("data", []) if not m["id"].startswith(".")]
            print(f"\nLocalAI visible models ({len(ids)}):")
            for mid in ids:
                print(f"     * {mid}")
    except Exception:
        print("\n  [WARN] LocalAI not reachable on localhost:8080")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Download GGUF models for LocalAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/download_models.py --status
  python scripts/download_models.py --model gemma-3-4b
  python scripts/download_models.py --model gemma-3-12b
  python scripts/download_models.py --model gemma-4-31b-q3   # lighter Gemma 4
  python scripts/download_models.py --model all

After download, restart LocalAI:
  docker compose restart localai
  curl http://localhost:8080/v1/models
        """
    )
    parser.add_argument(
        "--model", "-m",
        choices=list(MODELS.keys()) + ["all"],
        default=None,
        help="Model to download",
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show download status and exit",
    )
    parser.add_argument(
        "--token", "-t",
        default="",
        help="HuggingFace token for gated models. Also reads HF_TOKEN env var.",
    )
    args = parser.parse_args()

    global _HF_TOKEN
    _HF_TOKEN = args.token or os.environ.get("HF_TOKEN", "")
    if _HF_TOKEN:
        print(f"  HF token: provided (len={len(_HF_TOKEN)})")

    if args.status or args.model is None:
        all_ok = check_status()
        if args.model is None:
            sys.exit(0 if all_ok else 1)

    targets = list(MODELS.keys()) if args.model == "all" else [args.model]

    need_download = [k for k in targets
                     if not os.path.exists(os.path.join(MODELS_DIR, MODELS[k]["filename"]))]
    total_gb = sum(MODELS[k]["size_gb"] for k in need_download)

    print(f"\nDownloading: {', '.join(targets)}")
    if total_gb > 0:
        print(f"Total size: ~{total_gb:.1f} GB -- ensure sufficient disk space")

    results = {}
    for key in targets:
        results[key] = download_model(key, MODELS[key], _HF_TOKEN)

    print(f"\n{'='*65}")
    print("  Summary")
    print(f"{'='*65}")
    for key, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status}  {key} -- {MODELS[key]['filename']}")

    print("\nNext steps:")
    print("  1. docker compose restart localai")
    print("  2. curl http://localhost:8080/v1/models")
    print("  3. Edit .env: MODEL_NAME=gemma-3-4b-it  (or gemma-3-12b-it)")
    print("  4. docker compose restart backend")
    print()

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
