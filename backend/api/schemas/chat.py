from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    organisation: Optional[str] = ""

class ChatResponse(BaseModel):
    response: str
    session_id: str
