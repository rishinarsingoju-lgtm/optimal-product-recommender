from typing import Any

from backend.services.normalization import merge_structured_queries, normalize_query


NEGATIVE_BRAND_RESPONSES = {
    "no",
    "nope",
    "none",
    "any",
    "anything",
    "no preference",
    "no preferred brand",
    "all",
}


def handle_chat(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    previous_query = context.get("structured_query") or {}
    pending_question = context.get("pending_question")

    normalized = normalize_query(message)
    text = message.strip().lower()

    if pending_question == "brand" and text in NEGATIVE_BRAND_RESPONSES:
        normalized["brand"] = None
        context["brand_skipped"] = True

    structured_query = merge_structured_queries(previous_query, normalized)
    context["structured_query"] = structured_query

    missing_product = not structured_query.get("product_type")
    missing_budget = not structured_query.get("budget")
    missing_brand = not structured_query.get("brand") and not context.get("brand_skipped")

    if missing_product:
        context["pending_question"] = "product_type"
        return _response(
            "What product should I compare?",
            context,
            structured_query,
            needs_clarification=True,
            missing_fields=["product_type"],
        )

    if missing_budget:
        context["pending_question"] = "budget"
        return _response(
            "What is your budget?",
            context,
            structured_query,
            needs_clarification=True,
            missing_fields=["budget"],
        )

    should_ask_brand = missing_brand and pending_question == "budget"
    if should_ask_brand:
        context["pending_question"] = "brand"
        return _response(
            "Any preferred brand? You can say no preference.",
            context,
            structured_query,
            needs_clarification=True,
            missing_fields=["brand"],
        )

    context["pending_question"] = None
    reply = _ready_message(structured_query)
    return _response(
        reply,
        context,
        structured_query,
        needs_clarification=False,
        ready_to_search=True,
        missing_fields=[],
    )


def _response(
    reply: str,
    context: dict[str, Any],
    structured_query: dict[str, Any],
    needs_clarification: bool,
    missing_fields: list[str],
    ready_to_search: bool = False,
) -> dict[str, Any]:
    return {
        "reply": reply,
        "context": context,
        "structured_query": structured_query,
        "needs_clarification": needs_clarification,
        "ready_to_search": ready_to_search,
        "missing_fields": missing_fields,
    }


def _ready_message(structured_query: dict[str, Any]) -> str:
    product_type = structured_query.get("product_type") or "products"
    budget = structured_query.get("budget")
    brand = structured_query.get("brand")

    label = _product_label(product_type, brand)
    pieces = [f"Searching for {label}"]
    if budget:
        pieces.append(f"up to INR {int(budget):,}")
    return " ".join(pieces) + "."


def _product_label(product_type: str, brand: str | None) -> str:
    if product_type == "phone" and brand == "Apple":
        return "iPhone models"
    if brand:
        return f"{brand} {product_type}s"
    if product_type == "phone":
        return "smartphones"
    return f"{product_type}s"
