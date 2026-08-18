"""Background watcher to automatically index document files in ISO_DOCS_PATH."""

import json
import os
import time
import logging
import threading
from pathlib import Path
from typing import Dict

from core.config import settings
from repositories.vector_store import VectorStore
from services.document_ingest import parse_bytes, chunk_text, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

STATUS_FILE = os.path.join(os.getenv("DATA_PATH", "/data"), ".indexed_files.json")


class DocumentWatcher(threading.Thread):
    def __init__(self, interval_seconds: int = 30):
        super().__init__(daemon=True, name="DocumentWatcherThread")
        self.interval_seconds = interval_seconds
        self.docs_dir = Path(settings.ISO_DOCS_PATH)
        self.running = False
        self._stop_event = threading.Event()

    def load_status(self) -> Dict[str, float]:
        if not os.path.exists(STATUS_FILE):
            return {}
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load indexed files status: {e}")
            return {}

    def save_status(self, status: Dict[str, float]):
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save indexed files status: {e}")

    def run(self):
        logger.info(f"DocumentWatcher started. Watching directory: {self.docs_dir}")
        self.running = True
        
        # Initial scan
        self.scan_and_index()

        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval_seconds)
            if self._stop_event.is_set():
                break
            self.scan_and_index()

        self.running = False
        logger.info("DocumentWatcher stopped.")

    def stop(self):
        self._stop_event.set()

    def scan_and_index(self):
        if not self.docs_dir.exists():
            os.makedirs(self.docs_dir, exist_ok=True)
            return

        status = self.load_status()
        status_changed = False

        # Get all files in directory
        try:
            files = [f for f in self.docs_dir.iterdir() if f.is_file()]
        except Exception as e:
            logger.error(f"Failed to read ISO_DOCS_PATH: {e}")
            return

        for file_path in files:
            ext = file_path.suffix.lower().lstrip(".")
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filename = file_path.name
            filepath_str = str(file_path.resolve())
            mtime = file_path.stat().st_mtime

            # Check if index is required
            if filepath_str not in status or mtime > status[filepath_str]:
                logger.info(f"New or modified file detected for RAG: {filename}")
                success = self.index_file(file_path)
                if success:
                    status[filepath_str] = mtime
                    status_changed = True

        if status_changed:
            self.save_status(status)

    def index_file(self, file_path: Path) -> bool:
        filename = file_path.name
        try:
            # Read and parse bytes
            data = file_path.read_bytes()
            text, _, _ = parse_bytes(data, filename)
            
            if not text.strip():
                logger.warning(f"Extracted empty text from file {filename}, skipping RAG indexing")
                return True # Mark as indexed to avoid repetitive warning

            # Chunk text
            chunks = chunk_text(text)
            if not chunks:
                logger.warning(f"No chunks created for file {filename}")
                return True

            # Prepare documents and metadata
            vs = VectorStore()
            collection = vs.get_collection("iso_documents")
            
            # Clean up old chunks for this file from collection
            collection.delete(where={"file": filename})

            all_chunks = [c.text for c in chunks]
            all_ids = [f"{file_path.stem}_{c.index}" for c in chunks]
            all_metadata = [
                {
                    "source": file_path.stem,
                    "file": filename,
                    "chunk_index": c.index,
                    "total_chunks": len(chunks),
                    "doc_title": text.split("\n")[0][:100].strip().lstrip("#").strip() or file_path.stem,
                }
                for c in chunks
            ]

            # Upsert chunks in batches of 100
            for i in range(0, len(all_chunks), 100):
                end = min(i + 100, len(all_chunks))
                collection.add(
                    documents=all_chunks[i:end],
                    ids=all_ids[i:end],
                    metadatas=all_metadata[i:end]
                )

            logger.info(f"Successfully indexed RAG SOC Playbook: {filename} into {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Failed to auto-index file {filename}: {e}", exc_info=True)
            return False


# Global watcher reference
_watcher = None
_watcher_lock = threading.Lock()


def start_watcher():
    global _watcher
    with _watcher_lock:
        if _watcher is None or not _watcher.is_alive():
            _watcher = DocumentWatcher()
            _watcher.start()


def stop_watcher():
    global _watcher
    with _watcher_lock:
        if _watcher is not None:
            _watcher.stop()
            _watcher = None
