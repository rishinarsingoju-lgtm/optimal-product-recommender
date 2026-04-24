from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.models.database import record_query, save_cached_results, save_products, get_cached_results
from backend.services.chat import handle_chat
from backend.services.normalization import (
    canonical_query_key,
    filter_products_for_query,
    limit_products_balanced,
    normalize_products,
)
from backend.services.ranking import rank_products
from backend.services.scraper import ProductScraper


SEARCH_CACHE_TTL_SECONDS = 60 * 60 * 12

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    context: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    structured_query: dict[str, Any]
    limit: int = Field(default=10, ge=1, le=20)
    sources: list[str] = Field(default_factory=lambda: ["amazon", "flipkart"])


class RankRequest(BaseModel):
    structured_query: dict[str, Any]
    products: list[dict[str, Any]]
    limit: int = Field(default=10, ge=1, le=20)


@router.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    response = handle_chat(request.message, request.context)
    record_query(request.message, response.get("structured_query") or {})
    return response


@router.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    sources = [source.lower() for source in request.sources if source.lower() in {"amazon", "flipkart"}]
    if not sources:
        sources = ["amazon", "flipkart"]

    query_key = canonical_query_key(request.structured_query, sources=sources)
    cached = get_cached_results(query_key, SEARCH_CACHE_TTL_SECONDS)
    if cached:
        return {
            "cached": True,
            "query_key": query_key,
            "products": cached[: request.limit],
            "errors": [],
        }

    scraper = ProductScraper(max_results_per_source=max(8, min(16, request.limit * 2)))
    scrape_result = scraper.scrape(request.structured_query, sources=sources)
    products = filter_products_for_query(
        normalize_products(scrape_result["products"]),
        request.structured_query,
    )
    products = limit_products_balanced(products, request.limit)

    if products:
        save_products(products)
        save_cached_results(query_key, products)

    return {
        "cached": False,
        "query_key": query_key,
        "products": products,
        "errors": scrape_result["errors"],
    }


@router.post("/rank")
def rank(request: RankRequest) -> dict[str, Any]:
    products = filter_products_for_query(
        normalize_products(request.products),
        request.structured_query,
    )
    ranked = rank_products(products, request.structured_query, limit=request.limit)
    if ranked:
        save_products(ranked)
    return {"products": ranked}
