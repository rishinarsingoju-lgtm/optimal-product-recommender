from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.models.database import get_product, init_db
from backend.routes.api import router as api_router


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


app = FastAPI(
    title="CompareIQ",
    description="Zero-cost product comparison and recommendation MVP.",
    version="0.1.0",
)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/product/{product_id}", response_class=HTMLResponse, name="product_detail")
def product_detail(product_id: str, request: Request) -> HTMLResponse:
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_url = str(request.url_for("product_detail", product_id=product_id))
    title = escape(product["name"])
    source = escape(product["source"])
    image = escape(product.get("image") or "")
    buy_url = escape(product.get("url") or "#")
    price = product.get("price") or 0
    rating = product.get("rating")
    rating_text = f"{rating:.1f}/5" if isinstance(rating, (int, float)) and rating else "Rating unavailable"
    description = escape(f"{source} product around INR {price:,.0f}. Rating: {rating_text}.")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | CompareIQ</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{title}">
  <meta property="og:image" content="{image}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{escape(product_url)}">
  <meta property="og:type" content="product">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <main class="detail-shell">
    <a class="back-link" href="/">Back to search</a>
    <section class="product-detail">
      <div class="detail-image-wrap">
        <img src="{image}" alt="{title}" class="detail-image" loading="eager" referrerpolicy="no-referrer">
      </div>
      <div class="detail-copy">
        <span class="source-pill">{source}</span>
        <h1>{title}</h1>
        <p class="detail-price">INR {price:,.0f}</p>
        <p class="detail-meta">{escape(rating_text)}</p>
        <a class="buy-link" href="{buy_url}" target="_blank" rel="noopener noreferrer">Buy Now</a>
      </div>
    </section>
  </main>
</body>
</html>"""
    return HTMLResponse(html)
