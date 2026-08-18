"""Standard Service — Dynamic loading, parsing, validation and ChromaDB indexing of custom compliance standards.

Supports JSON and YAML uploads. Each standard is stored as a JSON file in DATA_PATH/standards/
and optionally indexed into ChromaDB for RAG retrieval during assessment.

Schema for a custom standard:
{
  "id": "pci_dss_4",
  "name": "PCI-DSS 4.0 (Custom)",
  "version": "4.0",
  "description": "Payment Card Industry Data Security Standard",
  "controls": [
    {
      "category": "1. Network Security",
      "controls": [
        { "id": "1.1", "label": "Install firewall", "weight": "critical",
          "description": { "requirement": "...", "criteria": "...", "hint": "...", "evidence": ["..."] }
        }
      ]
    }
  ]
}
"""

import json
import os
import re
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.config import settings

logger = logging.getLogger(__name__)

STANDARDS_DIR = os.path.join(settings.DATA_PATH, "standards")
os.makedirs(STANDARDS_DIR, exist_ok=True)

# Allowed weight values
VALID_WEIGHTS = {"critical", "high", "medium", "low"}

# Weight scoring map (must match frontend WEIGHT_SCORE)
WEIGHT_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}


class StandardValidationError(Exception):
    """Raised when a standard file fails validation."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {'; '.join(errors)}")


def _sanitize_id(raw_id: str) -> str:
    """Sanitize standard ID to filesystem-safe slug."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_id.strip().lower())
    return cleaned[:64] or f"std_{uuid.uuid4().hex[:8]}"


def validate_standard(data: Dict[str, Any]) -> List[str]:
    """Validate a standard definition. Returns list of error messages (empty = valid)."""
    errors = []

    if not data.get("id"):
        errors.append("Missing required field: 'id'")
    if not data.get("name"):
        errors.append("Missing required field: 'name'")
    if not data.get("controls") or not isinstance(data["controls"], list):
        errors.append("Missing or invalid 'controls' array")
        return errors  # Can't validate further

    seen_ids = set()
    total_controls = 0

    for cat_idx, category in enumerate(data["controls"]):
        if not isinstance(category, dict):
            errors.append(f"controls[{cat_idx}] must be an object")
            continue
        if not category.get("category"):
            errors.append(f"controls[{cat_idx}] missing 'category' name")
        if not category.get("controls") or not isinstance(category["controls"], list):
            errors.append(f"controls[{cat_idx}] missing or invalid 'controls' array")
            continue

        for ctrl_idx, ctrl in enumerate(category["controls"]):
            if not isinstance(ctrl, dict):
                errors.append(f"controls[{cat_idx}].controls[{ctrl_idx}] must be an object")
                continue
            if not ctrl.get("id"):
                errors.append(f"controls[{cat_idx}].controls[{ctrl_idx}] missing 'id'")
            if not ctrl.get("label"):
                errors.append(f"controls[{cat_idx}].controls[{ctrl_idx}] missing 'label'")

            weight = ctrl.get("weight", "medium")
            if weight not in VALID_WEIGHTS:
                errors.append(f"Control '{ctrl.get('id', '?')}' has invalid weight '{weight}'. Must be: {VALID_WEIGHTS}")

            ctrl_id = ctrl.get("id", "")
            if ctrl_id in seen_ids:
                errors.append(f"Duplicate control ID: '{ctrl_id}'")
            seen_ids.add(ctrl_id)
            total_controls += 1

    if total_controls == 0:
        errors.append("Standard must have at least 1 control")

    if total_controls > 500:
        errors.append(f"Too many controls ({total_controls}). Maximum is 500")

    return errors


def parse_yaml_to_dict(content: str) -> Dict[str, Any]:
    """Parse YAML content to dict. Falls back to error if PyYAML not available."""
    try:
        import yaml
        return yaml.safe_load(content) or {}
    except ImportError:
        raise ValueError("YAML parsing requires PyYAML. Install with: pip install pyyaml")
    except Exception as e:
        raise ValueError(f"Invalid YAML: {str(e)}")


def parse_uploaded_standard(content: str, filename: str) -> Dict[str, Any]:
    """Parse uploaded file content (JSON or YAML) into a standard dict."""
    ext = Path(filename).suffix.lower()

    if ext in (".yaml", ".yml"):
        data = parse_yaml_to_dict(content)
    elif ext == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
    else:
        # Try JSON first, then YAML
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            try:
                data = parse_yaml_to_dict(content)
            except ValueError:
                raise ValueError(f"Unable to parse file as JSON or YAML: {filename}")

    if not isinstance(data, dict):
        raise ValueError("Parsed content must be a JSON/YAML object (not array or scalar)")

    return data


def save_standard(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and save a standard to disk. Returns the saved standard metadata."""
    # Ensure defaults
    if not data.get("id"):
        data["id"] = _sanitize_id(data.get("name", f"custom_{uuid.uuid4().hex[:8]}"))
    else:
        data["id"] = _sanitize_id(data["id"])

    # Set defaults for controls
    for category in data.get("controls", []):
        for ctrl in category.get("controls", []):
            if "weight" not in ctrl:
                ctrl["weight"] = "medium"
            # Ensure description is at least an empty dict
            if "description" not in ctrl:
                ctrl["description"] = {}

    # Validate
    errors = validate_standard(data)
    if errors:
        raise StandardValidationError(errors)

    # Calculate metadata
    all_controls = []
    for cat in data["controls"]:
        all_controls.extend(cat["controls"])

    total = len(all_controls)
    weight_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    max_score = 0
    for ctrl in all_controls:
        w = ctrl.get("weight", "medium")
        weight_breakdown[w] += 1
        max_score += WEIGHT_SCORE.get(w, 1)

    data["_metadata"] = {
        "total_controls": total,
        "max_weighted_score": max_score,
        "weight_breakdown": weight_breakdown,
        "categories": len(data["controls"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "upload",
    }

    # Save to file
    filepath = os.path.join(STANDARDS_DIR, f"{data['id']}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved standard '{data['id']}' ({total} controls, {len(data['controls'])} categories)")

    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "version": data.get("version", ""),
        "total_controls": total,
        "categories": len(data["controls"]),
        "max_weighted_score": max_score,
        "weight_breakdown": weight_breakdown,
        "filepath": filepath,
    }


def load_standard(standard_id: str) -> Optional[Dict[str, Any]]:
    """Load a standard by ID from disk."""
    filepath = os.path.join(STANDARDS_DIR, f"{standard_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_custom_standards() -> List[Dict[str, Any]]:
    """List all custom standards (metadata only, no full control trees)."""
    results = []
    for filename in sorted(os.listdir(STANDARDS_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(STANDARDS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("_metadata", {})
            results.append({
                "id": data.get("id", filename.replace(".json", "")),
                "name": data.get("name", "Unknown"),
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "total_controls": meta.get("total_controls", 0),
                "categories": meta.get("categories", 0),
                "max_weighted_score": meta.get("max_weighted_score", 0),
                "weight_breakdown": meta.get("weight_breakdown", {}),
                "created_at": meta.get("created_at", ""),
                "source": meta.get("source", "upload"),
            })
        except Exception as e:
            logger.warning(f"Failed to read standard {filename}: {e}")
    return results


def delete_standard(standard_id: str) -> bool:
    """Delete a custom standard by ID. Returns True if deleted."""
    # Prevent deleting built-in standards
    if standard_id in ("iso27001", "tcvn11930"):
        raise ValueError(f"Cannot delete built-in standard: {standard_id}")

    filepath = os.path.join(STANDARDS_DIR, f"{standard_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info(f"Deleted standard: {standard_id}")
        return True
    return False


def index_standard_to_chromadb(standard_id: str) -> Dict[str, Any]:
    """Index a custom standard's controls into its own ChromaDB domain collection for RAG retrieval.

    Each custom standard gets its own named collection (domain = standard_id) so
    assessments can query only the relevant standard without cross-contamination.
    """
    data = load_standard(standard_id)
    if not data:
        return {"status": "error", "message": f"Standard '{standard_id}' not found"}

    try:
        from repositories.vector_store import VectorStore
        vs = VectorStore()
        # Use the standard's own domain collection
        coll = vs.get_collection(standard_id)

        std_name = data.get("name", standard_id)
        chunks = []
        chunk_ids = []
        chunk_metas = []

        for cat in data.get("controls", []):
            category_name = cat.get("category", "Unknown")
            # Build a markdown-style chunk for each category
            lines = [f"# {std_name}", f"## {category_name}", ""]
            for ctrl in cat.get("controls", []):
                ctrl_id = ctrl.get("id", "")
                label = ctrl.get("label", "")
                weight = ctrl.get("weight", "medium")
                desc = ctrl.get("description", {})
                requirement = desc.get("requirement", "")
                criteria = desc.get("criteria", "")

                lines.append(f"### {ctrl_id} — {label} (Mức độ: {weight})")
                if requirement:
                    lines.append(f"**Yêu cầu:** {requirement}")
                if criteria:
                    lines.append(f"**Tiêu chí:** {criteria}")
                lines.append("")

            chunk_text = "\n".join(lines).strip()
            if chunk_text:
                chunk_id = f"custom_{standard_id}_{category_name.replace(' ', '_')}"
                chunks.append(chunk_text)
                chunk_ids.append(chunk_id)
                chunk_metas.append({
                    "source": f"custom_standard_{standard_id}",
                    "file": f"{standard_id}.json",
                    "doc_title": f"{std_name} — {category_name}",
                    "chunk_index": len(chunks) - 1,
                    "total_chunks": 0,  # Will be updated
                    "standard_id": standard_id,
                    "category": category_name,
                })

        # Update total_chunks in metadata
        for meta in chunk_metas:
            meta["total_chunks"] = len(chunks)

        if not chunks:
            return {"status": "error", "message": "No content to index"}

        # Remove all existing chunks for this standard (full re-index)
        try:
            existing = coll.get()
            if existing and existing["ids"]:
                coll.delete(ids=existing["ids"])
                logger.info(f"Removed {len(existing['ids'])} existing chunks for standard '{standard_id}'")
        except Exception:
            pass

        # Add new chunks into the domain-specific collection
        coll.add(
            documents=chunks,
            ids=chunk_ids,
            metadatas=chunk_metas
        )
        vs._initialized[standard_id] = True

        logger.info(f"Indexed standard '{standard_id}' → {len(chunks)} chunks into ChromaDB")
        return {
            "status": "ok",
            "standard_id": standard_id,
            "chunks_indexed": len(chunks),
            "categories": len(data.get("controls", [])),
        }

    except Exception as e:
        logger.error(f"ChromaDB indexing error for standard '{standard_id}': {e}")
        return {"status": "error", "message": str(e)}


def get_standard_for_frontend(standard_id: str) -> Optional[Dict[str, Any]]:
    """Get standard in frontend-compatible format (controls + controlDescriptions)."""
    data = load_standard(standard_id)
    if not data:
        return None

    # Build controls array (matching frontend ASSESSMENT_STANDARDS format)
    controls = []
    control_descriptions = {}

    for cat in data.get("controls", []):
        cat_entry = {
            "category": cat.get("category", ""),
            "controls": []
        }
        for ctrl in cat.get("controls", []):
            cat_entry["controls"].append({
                "id": ctrl.get("id", ""),
                "label": ctrl.get("label", ""),
                "weight": ctrl.get("weight", "medium"),
            })
            # Build description entry if available
            desc = ctrl.get("description", {})
            if desc and (desc.get("requirement") or desc.get("criteria")):
                control_descriptions[ctrl["id"]] = {
                    "requirement": desc.get("requirement", ""),
                    "criteria": desc.get("criteria", ""),
                    "hint": desc.get("hint", ""),
                    "evidence": desc.get("evidence", []),
                }

        controls.append(cat_entry)

    meta = data.get("_metadata", {})
    return {
        "id": data.get("id", standard_id),
        "name": data.get("name", ""),
        "version": data.get("version", ""),
        "description": data.get("description", ""),
        "controls": controls,
        "controlDescriptions": control_descriptions,
        "total_controls": meta.get("total_controls", 0),
        "max_weighted_score": meta.get("max_weighted_score", 0),
        "weight_breakdown": meta.get("weight_breakdown", {}),
    }


def generate_sample_standard() -> Dict[str, Any]:
    """Generate a sample standard JSON for user reference / download."""
    return {
        "id": "my_custom_standard",
        "name": "My Custom Security Standard v1.0",
        "version": "1.0",
        "description": "Example custom compliance standard with weighted controls",
        "controls": [
            {
                "category": "1. Access Control",
                "controls": [
                    {
                        "id": "AC.01",
                        "label": "Multi-Factor Authentication (MFA)",
                        "weight": "critical",
                        "description": {
                            "requirement": "All user accounts must have MFA enabled for system access.",
                            "criteria": "MFA is configured and enforced for 100% of user accounts.",
                            "hint": "Use TOTP, hardware keys, or push notifications. SMS is not recommended.",
                            "evidence": [
                                "MFA configuration screenshots",
                                "IAM policy document",
                                "User access audit report"
                            ]
                        }
                    },
                    {
                        "id": "AC.02",
                        "label": "Role-Based Access Control (RBAC)",
                        "weight": "high",
                        "description": {
                            "requirement": "Access to systems must be based on defined roles and least-privilege principle.",
                            "criteria": "RBAC is implemented with documented role definitions and periodic access reviews.",
                            "hint": "Review access quarterly. Remove unused accounts within 30 days of offboarding.",
                            "evidence": [
                                "Role definition matrix",
                                "Access review records",
                                "Offboarding checklist"
                            ]
                        }
                    },
                    {
                        "id": "AC.03",
                        "label": "Password Policy",
                        "weight": "medium",
                        "description": {
                            "requirement": "Strong password policies must be enforced across all systems.",
                            "criteria": "Minimum 12 characters, complexity requirements, no password reuse (last 12).",
                            "hint": "Consider passwordless authentication as an alternative.",
                            "evidence": ["Password policy document", "GPO/IAM screenshots"]
                        }
                    }
                ]
            },
            {
                "category": "2. Data Protection",
                "controls": [
                    {
                        "id": "DP.01",
                        "label": "Data Encryption at Rest",
                        "weight": "critical",
                        "description": {
                            "requirement": "All sensitive data must be encrypted at rest using AES-256 or equivalent.",
                            "criteria": "Encryption is enabled on all databases, file stores, and backup media.",
                            "hint": "Use TDE for databases, BitLocker/LUKS for disk, KMS for key management.",
                            "evidence": ["Encryption configuration audit", "KMS key rotation logs"]
                        }
                    },
                    {
                        "id": "DP.02",
                        "label": "Data Classification",
                        "weight": "high",
                        "description": {
                            "requirement": "All data assets must be classified according to sensitivity levels.",
                            "criteria": "Data classification policy exists and is applied to all data repositories.",
                            "hint": "Common levels: Public, Internal, Confidential, Restricted.",
                            "evidence": ["Data classification policy", "Data inventory with classifications"]
                        }
                    },
                    {
                        "id": "DP.03",
                        "label": "Backup & Recovery",
                        "weight": "high",
                        "description": {
                            "requirement": "Regular backups with tested recovery procedures (3-2-1 rule).",
                            "criteria": "Daily backups, tested monthly, off-site copy, RTO < 4h, RPO < 1h.",
                            "hint": "Follow 3-2-1 rule: 3 copies, 2 media types, 1 offsite.",
                            "evidence": ["Backup schedule", "Recovery test reports", "RTO/RPO documentation"]
                        }
                    }
                ]
            },
            {
                "category": "3. Incident Response",
                "controls": [
                    {
                        "id": "IR.01",
                        "label": "Incident Response Plan",
                        "weight": "critical",
                        "description": {
                            "requirement": "Documented IRP with defined roles, escalation paths, and communication plan.",
                            "criteria": "IRP is documented, approved by management, and tested annually.",
                            "hint": "Include playbooks for top 5 threat scenarios (ransomware, phishing, etc.).",
                            "evidence": ["IRP document", "Annual drill report", "Lessons learned records"]
                        }
                    },
                    {
                        "id": "IR.02",
                        "label": "Security Monitoring (SIEM)",
                        "weight": "critical",
                        "description": {
                            "requirement": "Centralized log monitoring with alerting for security events.",
                            "criteria": "SIEM deployed, logs from all critical systems, 24/7 alerting, 12-month retention.",
                            "hint": "Consider Wazuh, Splunk, or Elastic SIEM. Define correlation rules for common attacks.",
                            "evidence": ["SIEM dashboard screenshots", "Alert rule documentation", "Log retention policy"]
                        }
                    },
                    {
                        "id": "IR.03",
                        "label": "Vulnerability Management",
                        "weight": "high",
                        "description": {
                            "requirement": "Regular vulnerability scanning and patch management process.",
                            "criteria": "Weekly scans, critical patches within 72h, quarterly penetration testing.",
                            "hint": "Use Nessus, Qualys, or OpenVAS. Track remediation SLAs by severity.",
                            "evidence": ["Scan reports", "Patch management records", "Pentest reports"]
                        }
                    }
                ]
            }
        ]
    }
