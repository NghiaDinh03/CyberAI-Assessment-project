from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.chat_service import ChatService
import uuid
import json
import os
from datetime import datetime, timezone

router = APIRouter()

ASSESSMENTS_DIR = os.getenv("DATA_PATH", "./data") + "/assessments"
os.makedirs(ASSESSMENTS_DIR, exist_ok=True)

class SystemInfo(BaseModel):
    org_name: str = ""
    org_size: str = ""
    industry: str = ""
    servers: int = 0
    firewalls: str = ""
    vpn: bool = False
    cloud_provider: str = ""
    antivirus: str = ""
    backup_solution: str = ""
    siem: str = ""
    network_diagram: str = ""
    existing_policies: List[str] = []
    incidents_12m: int = 0
    employees: int = 0
    it_staff: int = 0
    iso_status: str = ""
    notes: str = ""

def save_assessment(assessment_id: str, data: dict):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_assessment(assessment_id: str) -> Optional[dict]:
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_assessments() -> List[dict]:
    results = []
    for filename in os.listdir(ASSESSMENTS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ASSESSMENTS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "id": data.get("id"),
                        "status": data.get("status"),
                        "org_name": data.get("system_info", {}).get("organization", {}).get("name", "Unknown"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    })
            except:
                pass
    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

def process_assessment_bg(assessment_id: str, system_data: dict):
    # Load current to update status
    data = load_assessment(assessment_id)
    if not data:
        return
    
    data["status"] = "processing"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_assessment(assessment_id, data)
    
    try:
        result = ChatService.assess_system(system_data)
        
        data["status"] = "completed"
        data["result"] = result
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_assessment(assessment_id, data)
        
    except Exception as e:
        data["status"] = "failed"
        data["error"] = str(e)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_assessment(assessment_id, data)

@router.post("/iso27001/assess")
async def assess(data: SystemInfo, background_tasks: BackgroundTasks):
    assessment_id = str(uuid.uuid4())
    system_data = {
        "organization": {
            "name": data.org_name,
            "size": data.org_size,
            "industry": data.industry,
            "employees": data.employees,
            "it_staff": data.it_staff
        },
        "infrastructure": {
            "servers": data.servers,
            "firewalls": data.firewalls,
            "vpn": "Có" if data.vpn else "Không",
            "cloud": data.cloud_provider or "Không sử dụng",
            "antivirus": data.antivirus or "Không có",
            "backup": data.backup_solution or "Không có",
            "siem": data.siem or "Không có",
            "network_diagram": data.network_diagram or "Không cung cấp"
        },
        "compliance": {
            "iso_status": data.iso_status or "Chưa triển khai",
            "existing_policies": data.existing_policies or ["Không có"],
            "incidents_12m": data.incidents_12m
        },
        "notes": data.notes
    }

    assessment_record = {
        "id": assessment_id,
        "status": "pending", # pending, processing, completed, failed
        "system_info": system_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    save_assessment(assessment_id, assessment_record)
    background_tasks.add_task(process_assessment_bg, assessment_id, system_data)
    
    return {"status": "accepted", "id": assessment_id, "message": "Assessment task started in background"}

@router.get("/iso27001/assessments")
async def get_all_assessments():
    return list_assessments()

@router.get("/iso27001/assessments/{assessment_id}")
async def get_assessment(assessment_id: str):
    data = load_assessment(assessment_id)
    if not data:
        return {"error": "Assessment not found", "status": "not_found"}
    return data

@router.delete("/iso27001/assessments/{assessment_id}")
async def delete_assessment(assessment_id: str):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return {"status": "success", "message": "Assessment deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to delete file: {str(e)}"}
    return {"status": "not_found", "message": "Assessment not found"}

@router.post("/iso27001/reindex")
async def reindex():
    vs = ChatService.get_vector_store()
    result = vs.index_documents()
    return result

@router.get("/iso27001/chromadb/stats")
async def chromadb_stats():
    try:
        vs = ChatService.get_vector_store()
        count = vs.collection.count()
        metadata = vs.collection.metadata
        peek = vs.collection.peek(limit=3)
        sources = set()
        if peek and peek.get('metadatas'):
            for m in peek['metadatas']:
                if m and m.get('source'):
                    sources.add(m['source'])

        docs_dir = os.getenv("ISO_DOCS_PATH", "/data/iso_documents")
        files = []
        from pathlib import Path
        docs_path = Path(docs_dir)
        if docs_path.exists():
            for f in docs_path.glob("*.md"):
                files.append({
                    "name": f.name,
                    "size_bytes": f.stat().st_size
                })

        return {
            "status": "ok",
            "total_chunks": count,
            "total_files": len(files),
            "files": files,
            "collection_name": "iso_documents",
            "metric": metadata.get("hnsw:space", "unknown"),
            "sample_sources": list(sources)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/iso27001/chromadb/search")
async def chromadb_search(query: dict):
    try:
        vs = ChatService.get_vector_store()
        q = query.get("query", "")
        top_k = query.get("top_k", 3)
        if not q:
            return {"status": "error", "message": "Missing query parameter"}
        results = vs.search(q, top_k=top_k)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

