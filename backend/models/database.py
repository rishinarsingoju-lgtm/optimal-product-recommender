import json
import sqlite3
import time
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent / "app.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                price REAL,
                rating REAL,
                reviews_count INTEGER DEFAULT 0,
                source TEXT NOT NULL,
                image TEXT,
                url TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_url_source
            ON products(source, url);

            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_input TEXT NOT NULL,
                normalized_query TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cached_results (
                query_key TEXT PRIMARY KEY,
                products_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )


def record_query(raw_input: str, normalized_query: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO queries(raw_input, normalized_query, created_at)
            VALUES (?, ?, ?)
            """,
            (raw_input, json.dumps(normalized_query), int(time.time())),
        )


def save_products(products: list[dict[str, Any]]) -> None:
    if not products:
        return

    now = int(time.time())
    rows = [
        (
            item["id"],
            item["name"],
            item.get("normalized_name") or item["name"].lower(),
            item.get("price"),
            item.get("rating"),
            item.get("reviews_count") or 0,
            item.get("source") or "unknown",
            item.get("image"),
            item.get("url"),
            now,
        )
        for item in products
    ]

    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO products(
                id, name, normalized_name, price, rating, reviews_count,
                source, image, url, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                normalized_name = excluded.normalized_name,
                price = excluded.price,
                rating = excluded.rating,
                reviews_count = excluded.reviews_count,
                source = excluded.source,
                image = excluded.image,
                url = excluded.url,
                created_at = excluded.created_at
            """,
            rows,
        )


def get_product(product_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return dict(row) if row else None


def get_cached_results(query_key: str, ttl_seconds: int) -> list[dict[str, Any]] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT products_json, created_at FROM cached_results WHERE query_key = ?",
            (query_key,),
        ).fetchone()

    if not row:
        return None

    if int(time.time()) - int(row["created_at"]) > ttl_seconds:
        return None

    try:
        return json.loads(row["products_json"])
    except json.JSONDecodeError:
        return None


def save_cached_results(query_key: str, products: list[dict[str, Any]]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO cached_results(query_key, products_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(query_key) DO UPDATE SET
                products_json = excluded.products_json,
                created_at = excluded.created_at
            """,
            (query_key, json.dumps(products), int(time.time())),
        )
