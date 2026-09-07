"""Evidence Parser Engine — Multi-format file extraction with OCR fallback and encoding resilience."""

import io
import json
import logging
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Max content characters extracted per file to inject into LLM prompts
MAX_EVIDENCE_CHARS = 10000
# Max file size: 50MB
MAX_EVIDENCE_SIZE_BYTES = 50 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    # Text
    ".txt", ".log", ".csv", ".json", ".conf", ".xml", ".md", ".ini", ".yaml", ".yml",
    # Documents
    ".pdf", ".docx", ".doc", ".xlsx",
    # Images
    ".png", ".jpg", ".jpeg", ".webp"
}


def _safe_clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    if not text:
        return ""
    # Replace control characters except newline and tab
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return cleaned.strip()


def parse_text_file(content_bytes: bytes, filename: str) -> Tuple[str, Optional[str]]:
    """Decode text with encoding fallbacks (UTF-8, UTF-8-sig, CP1258, Latin-1)."""
    encodings = ["utf-8-sig", "utf-8", "cp1258", "latin-1", "ascii"]
    for enc in encodings:
        try:
            text = content_bytes.decode(enc)
            return _safe_clean_text(text), None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return "", f"Lỗi giải mã {enc}: {str(e)}"
    
    # Fallback with replace
    text = content_bytes.decode("utf-8", errors="replace")
    return _safe_clean_text(text), None


def parse_pdf_file(content_bytes: bytes, filename: str) -> Tuple[str, int, bool, Optional[str]]:
    """Extract text from PDF via pypdf with OCR fallback for scanned pages."""
    text_pieces = []
    page_count = 0
    ocr_applied = False
    error_msg = None

    try:
        from pypdf import PdfReader
        stream = io.BytesIO(content_bytes)
        reader = PdfReader(stream)
        page_count = len(reader.pages)

        for page_idx, page in enumerate(reader.pages[:80]):  # Process up to 80 pages (supports 50+ page audit reports)
            page_text = page.extract_text() or ""
            if len(page_text.strip()) > 10:
                text_pieces.append(f"[Trang {page_idx + 1}]\n{page_text.strip()}")
            else:
                # Page seems empty or scanned — try OCR if images available
                try:
                    import pytesseract
                    from PIL import Image
                    for img_idx, img_obj in enumerate(page.images):
                        img = Image.open(io.BytesIO(img_obj.data))
                        ocr_text = pytesseract.image_to_string(img, lang="vie+eng")
                        if ocr_text.strip():
                            ocr_applied = True
                            text_pieces.append(f"[Trang {page_idx + 1} (OCR)]\n{ocr_text.strip()}")
                except Exception:
                    # OCR unavailable or failed for page; non-fatal
                    pass

        extracted_text = "\n\n".join(text_pieces)
        return _safe_clean_text(extracted_text), page_count, ocr_applied, None

    except ImportError:
        return "[Lỗi hệ thống: Thư viện pypdf chưa được cài đặt]", 0, False, "PYPDF_NOT_INSTALLED"
    except Exception as e:
        logger.warning(f"[EvidenceParser] PDF extract error on {filename}: {e}")
        return f"[Lỗi đọc tệp PDF: {str(e)[:120]}]", page_count, False, str(e)


def parse_docx_file(content_bytes: bytes, filename: str) -> Tuple[str, Optional[str]]:
    """Extract paragraph and table cell text from DOCX preserving heading hierarchy and table rows."""
    try:
        from docx import Document
        stream = io.BytesIO(content_bytes)
        doc = Document(stream)
        text_lines = []

        # Paragraphs with heading structure
        for p in doc.paragraphs:
            t = p.text.strip()
            if t:
                style_name = getattr(p.style, "name", "") or ""
                if "Heading" in style_name or "Title" in style_name:
                    text_lines.append(f"\n### {t}")
                else:
                    text_lines.append(t)

        # Tables with expanded row limits for comprehensive audit reports
        for table_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(row_cells):
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                text_lines.append(f"\n[Bảng {table_idx + 1}]\n" + "\n".join(table_rows[:250]))

        return _safe_clean_text("\n".join(text_lines)), None
    except ImportError:
        return "[Lỗi hệ thống: Thư viện python-docx chưa được cài đặt]", "DOCX_LIB_MISSING"
    except Exception as e:
        logger.warning(f"[EvidenceParser] DOCX error on {filename}: {e}")
        return f"[Lỗi đọc tệp DOCX: {str(e)[:120]}]", str(e)


def parse_image_file(content_bytes: bytes, filename: str) -> Tuple[str, bool, Optional[str]]:
    """OCR image via Tesseract if available, else describe metadata."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content_bytes))
        width, height = img.size
        meta_str = f"[Ảnh: {filename} — Kích thước: {width}x{height}, Định dạng: {img.format}]"

        try:
            import pytesseract
            # Try Vietnamese + English OCR, fallback to English only
            try:
                ocr_text = pytesseract.image_to_string(img, lang="vie+eng")
            except Exception:
                ocr_text = pytesseract.image_to_string(img, lang="eng")
            
            if ocr_text and len(ocr_text.strip()) > 5:
                return f"{meta_str}\n\n[Văn bản trích xuất OCR]:\n{ocr_text.strip()}", True, None
            return f"{meta_str}\n(Không phát hiện văn bản rõ ràng trong ảnh)", False, None

        except ImportError:
            return f"{meta_str}\n(Pytesseract chưa được cài đặt — đã đính kèm ảnh minh chứng gốc)", False, "OCR_LIB_NOT_INSTALLED"
        except Exception as ocr_err:
            # Tesseract binary not found in OS path
            err_str = str(ocr_err)
            if "tesseract is not installed" in err_str.lower() or "not found" in err_str.lower():
                return f"{meta_str}\n(Tesseract OCR engine chưa được kích hoạt trên máy chủ — đã lưu minh chứng)", False, "TESSERACT_BINARY_MISSING"
            return f"{meta_str}\n[OCR Lỗi: {err_str[:100]}]", False, err_str

    except Exception as e:
        logger.warning(f"[EvidenceParser] Image error on {filename}: {e}")
        return f"[Lỗi đọc tệp ảnh: {str(e)[:100]}]", False, str(e)


def parse_evidence_file(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Universal parser for single evidence file with robust error encapsulation."""
    _, ext = os.path.splitext(filename.lower())
    size_bytes = len(content_bytes)

    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "filename": filename,
            "status": "unsupported",
            "parsed_text": f"[Định dạng '{ext}' không được hỗ trợ]",
            "char_count": 0,
            "page_count": 0,
            "ocr_applied": False,
            "error_code": "UNSUPPORTED_FORMAT",
            "error_message": f"Định dạng '{ext}' không nằm trong danh sách hỗ trợ."
        }

    if size_bytes > MAX_EVIDENCE_SIZE_BYTES:
        return {
            "filename": filename,
            "status": "failed",
            "parsed_text": f"[Kích thước tệp ({size_bytes // 1024}KB) vượt quá giới hạn 50MB]",
            "char_count": 0,
            "page_count": 0,
            "ocr_applied": False,
            "error_code": "FILE_TOO_LARGE",
            "error_message": f"Kích thước vượt quá {MAX_EVIDENCE_SIZE_BYTES // (1024*1024)}MB."
        }

    parsed_result = None

    # 1. Text extensions
    if ext in {".txt", ".log", ".csv", ".json", ".conf", ".xml", ".md", ".ini", ".yaml", ".yml"}:
        text, err = parse_text_file(content_bytes, filename)
        status = "success" if text and not err else ("failed" if err else "success")
        parsed_result = {
            "filename": filename,
            "status": status,
            "parsed_text": text[:MAX_EVIDENCE_CHARS],
            "full_text": text,
            "char_count": len(text),
            "page_count": 1,
            "ocr_applied": False,
            "error_code": err,
            "error_message": err
        }

    # 2. PDF
    elif ext == ".pdf":
        text, page_count, ocr_applied, err = parse_pdf_file(content_bytes, filename)
        status = "success" if not err else "failed"
        parsed_result = {
            "filename": filename,
            "status": status,
            "parsed_text": text[:MAX_EVIDENCE_CHARS],
            "full_text": text,
            "char_count": len(text),
            "page_count": page_count,
            "ocr_applied": ocr_applied,
            "error_code": err,
            "error_message": err
        }

    # 3. DOCX
    elif ext in {".docx", ".doc"}:
        text, err = parse_docx_file(content_bytes, filename)
        status = "success" if not err else "failed"
        parsed_result = {
            "filename": filename,
            "status": status,
            "parsed_text": text[:MAX_EVIDENCE_CHARS],
            "full_text": text,
            "char_count": len(text),
            "page_count": 1,
            "ocr_applied": False,
            "error_code": err,
            "error_message": err
        }

    # 4. Images
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        text, ocr_applied, err = parse_image_file(content_bytes, filename)
        status = "success"  # Image attachment itself succeeds even if OCR binary is not installed
        parsed_result = {
            "filename": filename,
            "status": status,
            "parsed_text": text[:MAX_EVIDENCE_CHARS],
            "full_text": text,
            "char_count": len(text),
            "page_count": 1,
            "ocr_applied": ocr_applied,
            "error_code": err,
            "error_message": err
        }

    if parsed_result is None:
        return {
            "filename": filename,
            "masked_filename": mask_evidence_filename(filename),
            "sha256": compute_file_sha256(content_bytes),
            "status": "failed",
            "parsed_text": "[Không thể phân tích định dạng này]",
            "char_count": 0,
            "page_count": 0,
            "ocr_applied": False,
            "error_code": "UNKNOWN_ERROR",
            "error_message": "Không thể xử lý tệp"
        }

    parsed_result["sha256"] = compute_file_sha256(content_bytes)
    parsed_result["masked_filename"] = mask_evidence_filename(filename)

    # Agent 1 Fact Extraction: enrich parsed_result with structured SecurityFactCard
    try:
        from services.evidence_fact_extractor import EvidenceFactExtractor
        raw_to_extract = parsed_result.get("full_text") or parsed_result.get("parsed_text", "")
        fact_card = EvidenceFactExtractor.extract_facts(raw_to_extract, filename, use_llm=False)
        parsed_result["fact_card"] = fact_card.to_dict()
        parsed_result["fact_summary"] = fact_card.to_compact_summary()
    except Exception as fact_err:
        logger.warning(f"[EvidenceParser] Fact extraction error on {filename}: {fact_err}")
        parsed_result["fact_card"] = {}
        parsed_result["fact_summary"] = ""

    return parsed_result


def compute_file_sha256(content_bytes: bytes) -> str:
    """Compute SHA-256 hex digest of file bytes for verifiable evidence manifest."""
    import hashlib
    return hashlib.sha256(content_bytes or b"").hexdigest()


def mask_evidence_filename(filename: str) -> str:
    """Mask IP addresses, internal hostnames, and credentials in evidence filenames for public audit export."""
    safe = os.path.basename(filename)
    # Mask IPv4 addresses: 10.140.0.103 -> 10.140.***.***
    safe = re.sub(r'(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}', r'\1***.***', safe)
    # Mask potential token or hex hashes >= 12 chars
    safe = re.sub(r'\b[a-f0-9]{12,}\b', r'***', safe, flags=re.IGNORECASE)
    return safe
