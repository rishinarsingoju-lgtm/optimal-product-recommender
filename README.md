# CompareIQ

CompareIQ is a zero-cost MVP product comparison and recommendation engine.

It uses:

- Python + FastAPI
- SQLite
- HTML, CSS, and vanilla JavaScript
- Selenium for Amazon and Flipkart scraping
- Rule-based NLP for query normalization
- Local ranking logic with no paid APIs

## Run Locally

On Windows, the easiest path is:

```powershell
.\run_app.bat
```

Then open http://127.0.0.1:8000.

Manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

Selenium needs a local Chromium browser. Install Google Chrome or Microsoft Edge if Selenium cannot start a browser.

## API

### POST /chat

```json
{
  "message": "best phone under 20000",
  "context": {}
}
```

Returns a bot reply, the session context, and a structured query.

### POST /search

```json
{
  "structured_query": {
    "category": "electronics",
    "product_type": "phone",
    "budget": 20000,
    "brand": null,
    "features": ["best"]
  },
  "limit": 10,
  "sources": ["amazon", "flipkart"]
}
```

Scrapes products, normalizes them, stores them, and caches the result.

### POST /rank

```json
{
  "structured_query": {
    "product_type": "phone",
    "budget": 20000,
    "features": ["best"]
  },
  "products": []
}
```

Returns ranked products with score breakdowns.

## Notes

Scraping selectors can change when Amazon or Flipkart update their pages, and both sites may block automated traffic. The app retries politely, uses headless Selenium, caches repeated queries for 12 hours, and reports scraping failures back to the UI.
