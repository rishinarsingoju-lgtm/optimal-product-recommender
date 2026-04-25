# CompareIQ 🛍️

> A zero-cost MVP product comparison and recommendation engine powered by conversational AI. Get personalized product recommendations from Amazon and Flipkart without leaving your browser.

**Status:** MVP | **License:** MIT | **Python:** 3.8+

## ✨ Features

- **Conversational Search** - Natural language queries like "best phone under 30000" 
- **Multi-Store Scraping** - Aggregates products from Amazon and Flipkart in real-time
- **Intelligent Ranking** - Rule-based scoring with no paid APIs required
- **Smart Caching** - 12-hour cache for repeated queries, fast responses
- **Modern UI** - Clean, responsive interface with smooth animations
- **Session Context** - Maintains conversation history for refined searches
- **Error Resilience** - Graceful fallbacks when scraping fails

## 🏗️ Architecture

```
CompareIQ
├── Frontend (HTML/CSS/JavaScript)
│   ├── Chat interface for natural language input
│   ├── Real-time product grid display
│   └── Responsive mobile-first design
│
├── Backend (FastAPI + Python)
│   ├── /chat - NLP query processing with context
│   ├── /search - Multi-source product scraping & caching
│   ├── /rank - Intelligent ranking algorithm
│   └── /product - Product detail pages
│
└── Data Layer (SQLite)
    ├── Product cache (12-hour TTL)
    ├── Search history
    └── Session context storage
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Google Chrome or Microsoft Edge (for Selenium)
- 200MB free disk space

### Option 1: Auto Setup (Windows)

```powershell
.\run_app.bat
```

Then open http://127.0.0.1:8000

### Option 2: Manual Setup (All Platforms)

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate (Windows)
.\.venv\Scripts\Activate.ps1

# 3. Or activate (Mac/Linux)
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000

## 📁 Project Structure

```
optimal-product-recommender/
├── backend/
│   ├── app.py                 # FastAPI app entry point
│   ├── app.sqlite3            # SQLite database
│   ├── models/
│   │   └── database.py        # DB models & queries
│   ├── routes/
│   │   └── api.py            # API endpoints
│   └── services/
│       ├── chat.py           # NLP query processing
│       ├── normalization.py  # Text normalization
│       ├── ranking.py        # Product ranking logic
│       └── scraper.py        # Selenium web scraping
├── frontend/
│   ├── index.html            # Main UI
│   ├── script.js             # Client-side logic
│   └── styles.css            # Design & animations
├── requirements.txt          # Python dependencies
└── run_app.bat              # Windows launcher script
```

## 🔌 API Reference

### POST `/chat` - Process natural language query

Process a user message and return a bot reply with structured query information.

**Request:**
```json
{
  "message": "best phone under 30000",
  "context": {}
}
```

**Response:**
```json
{
  "reply": "I'll search for phones under ₹30,000...",
  "context": {
    "history": ["best phone under 30000"],
    "last_product_type": "phone"
  },
  "structured_query": {
    "product_type": "phone",
    "budget": 30000,
    "brand": null,
    "features": []
  },
  "ready_to_search": true
}
```

### POST `/search` - Scrape and cache products

Scrapes products from multiple sources, normalizes data, and caches results.

**Request:**
```json
{
  "structured_query": {
    "product_type": "phone",
    "budget": 30000,
    "brand": null,
    "features": []
  },
  "limit": 10,
  "sources": ["amazon", "flipkart"]
}
```

**Response:**
```json
{
  "products": [
    {
      "id": "amazon_B0123ABCD",
      "name": "Samsung Galaxy A51",
      "price": 28999,
      "rating": 4.2,
      "reviews_count": 1203,
      "image": "https://...",
      "url": "https://amazon.in/...",
      "source": "amazon"
    }
  ],
  "errors": [],
  "cached": false,
  "timestamp": "2026-04-25T14:30:00Z"
}
```

### POST `/rank` - Rank products by relevance

Applies scoring algorithm to rank products by value, ratings, and relevance.

**Request:**
```json
{
  "structured_query": {
    "product_type": "phone",
    "budget": 30000
  },
  "products": [...],
  "limit": 10
}
```

**Response:**
```json
{
  "products": [
    {
      "id": "amazon_B0123ABCD",
      "name": "Samsung Galaxy A51",
      "price": 28999,
      "score": 0.892,
      "score_breakdown": {
        "price_value": 0.85,
        "rating": 0.95,
        "reviews": 0.88
      }
    }
  ]
}
```

### GET `/product/{id}` - View product details

Get detailed information about a specific product.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Server
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Scraping
SCRAPE_TIMEOUT=30
CACHE_TTL=43200  # 12 hours in seconds
MAX_RETRIES=3

# Database
DATABASE_URL=sqlite:///backend/app.sqlite3
```

### Customizing Ranking

Edit `backend/services/ranking.py` to adjust the scoring weights:

```python
WEIGHTS = {
    'price_value': 0.40,    # Budget alignment
    'rating': 0.35,         # User ratings
    'reviews': 0.15,        # Review count
    'recency': 0.10         # Listing freshness
}
```

## 🔧 Development

### Running Tests

```bash
pytest backend/tests/ -v
```

### Debugging

Enable debug logging in `backend/app.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Adding a New Source

1. Add scraper in `backend/services/scraper.py`
2. Implement `scrape_products(query)` method
3. Register in `backend/routes/api.py`

## 🐛 Troubleshooting

### "Selenium cannot start browser"
- Install Google Chrome or Microsoft Edge
- Verify Chrome is in PATH: `where chrome` (Windows) or `which google-chrome` (Linux/Mac)
- Restart the app

### "Connection refused on port 8000"
- Another app is using port 8000
- Change port: `uvicorn backend.app:app --port 8001`

### "No products returned"
- Amazon/Flipkart may have blocked the IP
- Check scraper output in browser console
- Try again in a few minutes or from different network

### "Slow responses"
- First request always scrapes (slow)
- Subsequent requests use 12-hour cache (fast)
- Clear cache: delete `backend/app.sqlite3` and restart

## 📊 Performance

- **Chat Response:** < 500ms (cached)
- **Initial Search:** 5-15s (live scraping)
- **Cached Search:** < 500ms
- **Product Ranking:** < 200ms
- **Database:** SQLite handles 100K+ products

## 🔒 Security & Ethics

- **Rate Limiting:** Respectful scraping with delays
- **User-Agent:** Identifies as real browser
- **Caching:** Reduces repeated requests
- **Error Handling:** Graceful degradation when blocked
- **No Auth:** MVP has no authentication layer

⚠️ **Note:** Scraping may violate Amazon/Flipkart ToS. Use responsibly and for personal use only.

## 📝 Notes

- Scraping selectors can break when Amazon or Flipkart update their pages
- Both sites may block automated traffic; the app retries politely with caching
- Headless Selenium reduces detection; results are cached for 12 hours
- Scraping failures are reported back to the UI gracefully
- Works best on broadband connections; mobile/satellite may timeout

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 👤 Author

Built as a zero-cost MVP for intelligent product comparison.

---

**Last Updated:** April 2026 | **Version:** 1.0.0-MVP
