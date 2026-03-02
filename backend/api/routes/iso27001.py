from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.chat_service import ChatService

router = APIRouter()


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


@router.post("/iso27001/assess")
async def assess(data: SystemInfo):
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

    result = ChatService.assess_system(system_data)
    return result


@router.post("/iso27001/reindex")
async def reindex():
    vs = ChatService.get_vector_store()
    result = vs.index_documents()
    return result
