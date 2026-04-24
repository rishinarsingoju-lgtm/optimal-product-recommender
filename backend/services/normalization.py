import hashlib
import json
import re
from typing import Any


PRODUCT_KEYWORDS = {
    "phone": {
        "category": "electronics",
        "aliases": ["smartphone", "mobile phone", "mobile", "phone", "iphone", "android"],
    },
    "laptop": {
        "category": "electronics",
        "aliases": ["gaming laptop", "notebook", "macbook", "laptop"],
    },
    "shoes": {
        "category": "fashion",
        "aliases": ["running shoes", "sneakers", "sneaker", "shoe", "shoes"],
    },
    "headphones": {
        "category": "electronics",
        "aliases": ["earbuds", "headphones", "headset", "earphones"],
    },
    "watch": {
        "category": "electronics",
        "aliases": ["smartwatch", "watch"],
    },
}

PRODUCT_RELEVANCE = {
    "phone": {
        "include": [
            "smartphone",
            "mobile phone",
            "mobile",
            "iphone",
            "galaxy",
            "oneplus",
            "redmi",
            "realme",
            "vivo",
            "oppo",
            "motorola",
            "moto",
            "pixel",
            "iqoo",
            "poco",
            "nothing",
            "narzo",
            "lava",
            "infinix",
            "tecno",
            "honor",
        ],
        "patterns": [
            r"\biphone\s?\d+\b",
            r"\b\d+\s*gb\s+ram\b",
            r"\b\d+\s*gb\s+rom\b",
            r"\b5g\b",
        ],
        "exclude": [
            "charger",
            "adapter",
            "cable",
            "case",
            "cover",
            "screen guard",
            "tempered glass",
            "power bank",
            "earbuds",
            "earphones",
            "headphones",
            "watch",
            "strap",
            "holder",
            "stand",
            "mount",
            "keypad",
            "feature phone",
            "button phone",
        ],
    },
    "laptop": {
        "include": [
            "laptop",
            "notebook",
            "macbook",
            "chromebook",
            "thinkpad",
            "ideapad",
            "vivobook",
            "pavilion",
            "inspiron",
            "zenbook",
        ],
        "patterns": [r"\b\d+\s*gb\s+ram\b", r"\bssd\b", r"\bintel\b", r"\bryzen\b"],
        "exclude": ["charger", "adapter", "bag", "sleeve", "stand", "keyboard", "mouse", "skin"],
    },
    "shoes": {
        "include": ["shoe", "shoes", "sneaker", "sneakers", "running", "trainer"],
        "patterns": [],
        "exclude": ["socks", "laces", "insole", "cleaner", "bag"],
    },
    "headphones": {
        "include": ["headphone", "headphones", "earbuds", "earphones", "headset", "bluetooth"],
        "patterns": [],
        "exclude": ["case", "cover", "cable", "charger", "adapter"],
    },
    "watch": {
        "include": ["watch", "smartwatch"],
        "patterns": [],
        "exclude": ["strap", "band", "charger", "case", "cover"],
    },
}

BRAND_ALIASES = {
    "apple": "Apple",
    "iphone": "Apple",
    "macbook": "Apple",
    "samsung": "Samsung",
    "oneplus": "OnePlus",
    "xiaomi": "Xiaomi",
    "redmi": "Redmi",
    "realme": "Realme",
    "vivo": "Vivo",
    "oppo": "Oppo",
    "motorola": "Motorola",
    "google": "Google",
    "hp": "HP",
    "dell": "Dell",
    "lenovo": "Lenovo",
    "acer": "Acer",
    "asus": "Asus",
    "msi": "MSI",
    "nike": "Nike",
    "adidas": "Adidas",
    "puma": "Puma",
    "reebok": "Reebok",
    "bata": "Bata",
    "boat": "boAt",
    "sony": "Sony",
    "jbl": "JBL",
}

FEATURE_KEYWORDS = {
    "cheap": ["cheap", "budget", "affordable", "lowest price", "low price", "value"],
    "best": ["best", "top", "highest rated", "recommended"],
    "popular": ["popular", "trusted", "reviews", "most bought"],
    "gaming": ["gaming", "game"],
    "camera": ["camera", "photo", "photography"],
    "battery": ["battery", "backup"],
    "lightweight": ["lightweight", "light weight", "portable"],
    "running": ["running", "jogging"],
    "wireless": ["wireless", "bluetooth"],
}

STOP_WORDS = {
    "best",
    "under",
    "below",
    "less",
    "than",
    "cheap",
    "budget",
    "with",
    "for",
    "the",
    "and",
    "in",
    "rs",
    "inr",
}


def normalize_query(raw_query: str) -> dict[str, Any]:
    text = _normalize_text(raw_query)
    product_type, category = _detect_product(text)
    brand = _detect_brand(text)
    budget = _extract_budget(text)
    features = _detect_features(text)

    return {
        "category": category,
        "product_type": product_type,
        "budget": budget,
        "brand": brand,
        "features": features,
        "raw_query": raw_query.strip(),
    }


def merge_structured_queries(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})

    for key in ("category", "product_type", "budget", "brand"):
        value = update.get(key)
        if value is not None:
            merged[key] = value

    features = set(merged.get("features") or [])
    features.update(update.get("features") or [])
    merged["features"] = sorted(features)

    raw_parts = [merged.get("raw_query"), update.get("raw_query")]
    merged["raw_query"] = " ".join(part for part in raw_parts if part).strip()
    return merged


def build_search_query(structured_query: dict[str, Any]) -> str:
    parts = []
    brand = structured_query.get("brand")
    product_type = structured_query.get("product_type")
    budget = structured_query.get("budget")
    features = structured_query.get("features") or []

    search_product_term = _search_product_term(product_type, brand)
    if brand and search_product_term.lower() != str(brand).lower():
        parts.append(str(brand))
    if search_product_term:
        parts.append(search_product_term)

    useful_features = [feature for feature in features if feature not in {"cheap", "best", "popular"}]
    parts.extend(useful_features[:2])

    if budget:
        parts.extend(["under", str(int(float(budget)))])

    if not parts:
        parts.append(structured_query.get("raw_query") or "product")

    return " ".join(parts)


def canonical_query_key(structured_query: dict[str, Any], sources: list[str] | None = None) -> str:
    payload = {
        "cache_version": 6,
        "category": structured_query.get("category"),
        "product_type": structured_query.get("product_type"),
        "budget": structured_query.get("budget"),
        "brand": structured_query.get("brand"),
        "features": sorted(structured_query.get("features") or []),
        "sources": sorted(sources or []),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def filter_products_for_query(
    products: list[dict[str, Any]],
    structured_query: dict[str, Any],
) -> list[dict[str, Any]]:
    budget = structured_query.get("budget")
    filtered = [
        product
        for product in products
        if _matches_product_type(product, structured_query) and _matches_brand(product, structured_query)
    ]

    if not budget:
        return filtered

    try:
        budget_value = float(budget)
    except (TypeError, ValueError):
        return filtered

    return [
        product
        for product in filtered
        if isinstance(product.get("price"), (int, float)) and product["price"] <= budget_value
    ]


def limit_products_balanced(products: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(products) <= limit:
        return products

    groups: dict[str, list[dict[str, Any]]] = {}
    source_order: list[str] = []
    for product in products:
        source = product.get("source") or "unknown"
        if source not in groups:
            groups[source] = []
            source_order.append(source)
        groups[source].append(product)

    selected: list[dict[str, Any]] = []
    index = 0
    while len(selected) < limit:
        added = False
        for source in source_order:
            group = groups[source]
            if index < len(group):
                selected.append(group[index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1
    return selected


def normalize_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in products:
        product = normalize_product(item)
        if product:
            normalized.append(product)
    return deduplicate_products(normalized)


def normalize_product(item: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_title(str(item.get("name") or item.get("title") or ""))
    if not title:
        return None

    price = parse_price(item.get("price"))
    rating = parse_rating(item.get("rating"))
    reviews_count = parse_reviews_count(item.get("reviews_count") or item.get("reviews"))
    source = str(item.get("source") or "unknown").strip().title()
    image = str(item.get("image") or "").strip()
    url = str(item.get("url") or "").strip()
    normalized_name = normalize_name(title)
    product_id = stable_product_id(source, url, normalized_name, price)

    return {
        "id": product_id,
        "name": title,
        "normalized_name": normalized_name,
        "price": price,
        "rating": rating,
        "reviews_count": reviews_count,
        "source": source,
        "image": image,
        "url": url,
    }


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"(?i)^sponsored\s*", "", title).strip()
    return title[:300]


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    tokens = [token for token in name.split() if token not in STOP_WORDS]
    return " ".join(tokens)


def parse_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1))


def parse_rating(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
        return rating if 0 <= rating <= 5 else None

    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None
    rating = float(match.group(1))
    return rating if 0 <= rating <= 5 else None


def parse_reviews_count(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, int):
        return max(value, 0)

    text = str(value).lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|k)?", text)
    if not match:
        return 0

    number = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        number *= 1_000
    elif suffix in {"lakh", "lac"}:
        number *= 100_000
    return int(number)


def deduplicate_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for product in products:
        key = _dedupe_key(product)
        current = by_key.get(key)
        if not current or _is_better_duplicate(product, current):
            by_key[key] = product
    return list(by_key.values())


def stable_product_id(source: str, url: str, normalized_name: str, price: float | None) -> str:
    if url:
        raw = "|".join([source.lower(), url])
    else:
        raw = "|".join([source.lower(), normalized_name, str(price or "")])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _detect_product(text: str) -> tuple[str | None, str | None]:
    for product_type, data in PRODUCT_KEYWORDS.items():
        aliases = sorted(data["aliases"], key=len, reverse=True)
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text):
                return product_type, data["category"]
    return None, None


def _detect_brand(text: str) -> str | None:
    for alias, brand in sorted(BRAND_ALIASES.items(), key=lambda pair: len(pair[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return brand
    return None


def _search_product_term(product_type: str | None, brand: str | None) -> str | None:
    if product_type == "phone":
        if brand == "Apple":
            return "iPhone"
        return "smartphone"
    return product_type


def _matches_product_type(product: dict[str, Any], structured_query: dict[str, Any]) -> bool:
    product_type = structured_query.get("product_type")
    if not product_type or product_type not in PRODUCT_RELEVANCE:
        return True

    title = product.get("normalized_name") or normalize_name(product.get("name") or "")
    rules = PRODUCT_RELEVANCE[product_type]
    includes = rules["include"]
    patterns = rules["patterns"]
    excludes = rules["exclude"]

    has_include = any(_contains_phrase(title, term) for term in includes)
    has_pattern = any(re.search(pattern, title) for pattern in patterns)

    if not has_include and not has_pattern:
        return False

    if any(_contains_phrase(title, term) for term in excludes):
        return False

    return True


def _matches_brand(product: dict[str, Any], structured_query: dict[str, Any]) -> bool:
    brand = structured_query.get("brand")
    if not brand:
        return True

    title = product.get("normalized_name") or normalize_name(product.get("name") or "")
    aliases = _brand_terms(brand)
    return any(_contains_phrase(title, alias) for alias in aliases)


def _brand_terms(brand: str) -> list[str]:
    terms = {brand.lower()}
    for alias, canonical in BRAND_ALIASES.items():
        if canonical == brand:
            terms.add(alias)
    return sorted(terms, key=len, reverse=True)


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalize_name(phrase)
    if not normalized_phrase:
        return False
    return re.search(rf"\b{re.escape(normalized_phrase)}\b", text) is not None


def _detect_features(text: str) -> list[str]:
    features = []
    for feature, aliases in FEATURE_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            features.append(feature)
    return sorted(set(features))


def _extract_budget(text: str) -> int | None:
    budget_patterns = [
        r"(?:under|below|less than|up to|upto|max|within|budget(?: is)?|around)\s*(?:rs\.?|inr|rupees|₹)?\s*(\d+(?:\.\d+)?)\s*(k|lakh|lac)?",
        r"(?:rs\.?|inr|rupees|₹)\s*(\d+(?:\.\d+)?)\s*(k|lakh|lac)?",
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, text)
        if match:
            return _scale_budget(match.group(1), match.group(2))

    whole_message_number = re.fullmatch(r"(?:rs\.?|inr|rupees|₹)?\s*(\d+(?:\.\d+)?)\s*(k|lakh|lac)?", text)
    if whole_message_number:
        return _scale_budget(whole_message_number.group(1), whole_message_number.group(2))

    return None


def _scale_budget(number_text: str, suffix: str | None) -> int:
    value = float(number_text)
    if suffix == "k":
        value *= 1_000
    elif suffix in {"lakh", "lac"}:
        value *= 100_000
    return int(value)


def _dedupe_key(product: dict[str, Any]) -> str:
    family_key = _product_family_key(product)
    if family_key:
        return family_key

    if product.get("url"):
        return f"url:{product['url']}"

    tokens = (product.get("normalized_name") or "").split()[:12]
    price = product.get("price")
    price_bucket = int(price // 100) if isinstance(price, (int, float)) else "unknown"
    return f"name:{' '.join(tokens)}:{price_bucket}"


def _is_better_duplicate(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_price = candidate.get("price") or float("inf")
    current_price = current.get("price") or float("inf")
    if candidate_price != current_price:
        return candidate_price < current_price
    return (candidate.get("rating") or 0) > (current.get("rating") or 0)


def _product_family_key(product: dict[str, Any]) -> str | None:
    name = product.get("normalized_name") or normalize_name(product.get("name") or "")

    iphone_match = re.search(r"\b(?:apple\s+)?iphone\s+(\d+)\s*(pro max|pro|plus|mini)?\b", name)
    if iphone_match:
        model = " ".join(part for part in iphone_match.groups() if part)
        storage = _first_storage(name)
        return f"phone:iphone:{model}:{storage}"

    phone_brands = [
        "samsung",
        "oneplus",
        "redmi",
        "xiaomi",
        "realme",
        "vivo",
        "oppo",
        "motorola",
        "moto",
        "pixel",
        "iqoo",
        "poco",
        "nothing",
        "lava",
        "infinix",
        "tecno",
        "honor",
    ]
    if any(re.search(rf"\b{brand}\b", name) for brand in phone_brands):
        storage = _first_storage(name)
        color_words = {
            "black",
            "white",
            "blue",
            "green",
            "silver",
            "gold",
            "pink",
            "red",
            "yellow",
            "purple",
            "grey",
            "gray",
            "titanium",
            "natural",
            "ultramarine",
            "sapphire",
            "matte",
            "lake",
            "forest",
            "starry",
        }
        tokens = [token for token in name.split() if token not in color_words]
        return f"phone:{' '.join(tokens[:8])}:{storage}"

    return None


def _first_storage(name: str) -> str:
    match = re.search(r"\b(\d+)\s*gb\b", name)
    return match.group(1) if match else "unknown"
