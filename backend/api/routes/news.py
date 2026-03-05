from fastapi import APIRouter, Query
from services.news_service import NewsService, _cache

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
    if os.path.exists(trans_path):
        shutil.rmtree(trans_path, ignore_errors=True)
    return {"status": "ok", "message": "Cache cleared"}
