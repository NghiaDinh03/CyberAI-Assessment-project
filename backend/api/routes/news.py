from fastapi import APIRouter, Query
from services.news_service import NewsService

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


@router.get("/news/all")
async def get_all_news(limit: int = Query(10, ge=1, le=30)):
    result = {}
    for cat in ["cybersecurity", "stocks_international", "stocks_vietnam"]:
        result[cat] = NewsService.get_news(cat, limit)
    return result
