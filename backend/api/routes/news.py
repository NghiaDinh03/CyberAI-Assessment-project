from fastapi import APIRouter, Query, Body, HTTPException
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel
from services.news_service import NewsService, _cache, get_ai_status
from services.summary_service import SummaryService, AUDIO_DIR

class SummaryRequest(BaseModel):
    url: str
    lang: str = "en"
    title: str = ""

class ReprocessRequest(BaseModel):
    url: str

router = APIRouter()


@router.get("/news")
async def get_news(
    category: str = Query("cybersecurity", description="cybersecurity | stocks_international | stocks_vietnam"),
    limit: int = Query(15, ge=1, le=50)
):
    return NewsService.get_news(category, limit)


@router.get("/news/categories")
async def get_categories():
    return NewsService.get_all_categories()


@router.get("/news/history")
async def get_news_history(category: str = Query("all", description="all | cybersecurity | stocks_international | stocks_vietnam")):
    """Lấy danh sách các bài báo đã cào trong vòng 7 ngày"""
    return NewsService.get_history(category)


@router.get("/news/ai-status")
async def get_news_ai_status():
    """Trả về trạng thái hiện tại của AI Worker (Đang dịch, tóm tắt...)"""
    return {"status": get_ai_status()}


@router.get("/news/search")
async def search_news(
    q: str = Query(..., min_length=1, description="Từ khóa tìm kiếm"),
    limit: int = Query(20, ge=1, le=50)
):
    return NewsService.search_news(q, limit)


@router.get("/news/all")
async def get_all_news(limit: int = Query(10, ge=1, le=30)):
    result = {}
    for cat in ["cybersecurity", "stocks_international", "stocks_vietnam"]:
        result[cat] = NewsService.get_news(cat, limit)
    return result


@router.post("/news/clear-cache")
async def clear_cache():
    _cache.clear()
    import os, shutil
    trans_path = "/data/translations"
    summary_path = "/data/summaries"
    if os.path.exists(trans_path):
        shutil.rmtree(trans_path, ignore_errors=True)
    if os.path.exists(summary_path):
        shutil.rmtree(summary_path, ignore_errors=True)
    return {"status": "ok", "message": "Cache cleared"}


@router.post("/news/summarize")
async def summarize_news(req: SummaryRequest):
    result = SummaryService.process_article(req.url, req.lang, req.title)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/news/reprocess")
async def reprocess_news(req: ReprocessRequest):
    result = NewsService.reprocess_article(req.url)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/news/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")
