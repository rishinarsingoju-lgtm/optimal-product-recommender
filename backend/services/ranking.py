import math
from typing import Any


def rank_products(
    products: list[dict[str, Any]],
    structured_query: dict[str, Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not products:
        return []

    weights = _weights_for_query(structured_query)
    max_reviews = max((product.get("reviews_count") or 0 for product in products), default=0)
    prices = [product.get("price") for product in products if isinstance(product.get("price"), (int, float))]
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None

    ranked = []
    for product in products:
        price_score = _price_score(product.get("price"), structured_query.get("budget"), min_price, max_price)
        rating_score = _rating_score(product.get("rating"))
        trust_score = _trust_score(product.get("reviews_count") or 0, max_reviews)

        score = (
            weights["price"] * price_score
            + weights["rating"] * rating_score
            + weights["reviews"] * trust_score
        )
        enriched = dict(product)
        enriched["score"] = round(score, 4)
        enriched["score_breakdown"] = {
            "price": round(price_score, 4),
            "rating": round(rating_score, 4),
            "trust": round(trust_score, 4),
            "weights": weights,
        }
        ranked.append(enriched)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def _weights_for_query(structured_query: dict[str, Any]) -> dict[str, float]:
    features = set(structured_query.get("features") or [])
    raw_query = str(structured_query.get("raw_query") or "").lower()

    weights = {"price": 0.4, "rating": 0.4, "reviews": 0.2}

    if "cheap" in features or any(term in raw_query for term in ("cheap", "budget", "affordable")):
        weights = {"price": 0.6, "rating": 0.25, "reviews": 0.15}
    elif "best" in features or "best" in raw_query or "top" in raw_query:
        weights = {"price": 0.25, "rating": 0.55, "reviews": 0.2}
    elif "popular" in features or "trusted" in raw_query:
        weights = {"price": 0.3, "rating": 0.3, "reviews": 0.4}

    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _price_score(
    price: float | None,
    budget: float | None,
    min_price: float | None,
    max_price: float | None,
) -> float:
    if not isinstance(price, (int, float)) or price <= 0:
        return 0.35

    if budget:
        budget = float(budget)
        if price <= budget:
            return max(0.0, min(1.0, 0.65 + 0.35 * ((budget - price) / budget)))
        return max(0.0, 0.65 - ((price - budget) / budget))

    if min_price is None or max_price is None or max_price == min_price:
        return 0.7
    return max(0.0, min(1.0, (max_price - price) / (max_price - min_price)))


def _rating_score(rating: float | None) -> float:
    if not isinstance(rating, (int, float)) or rating <= 0:
        return 0.45
    return max(0.0, min(1.0, rating / 5))


def _trust_score(reviews_count: int, max_reviews: int) -> float:
    if reviews_count <= 0:
        return 0.25
    if max_reviews <= 0:
        return 0.5
    return max(0.0, min(1.0, math.log10(reviews_count + 1) / math.log10(max_reviews + 1)))
