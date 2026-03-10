from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from scraper import scrape_all
from database import save_products, get_history
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# ✅ Add this route to serve index.html at "/"
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    products = scrape_all(query)
    if products:
        save_products(products)
    
    products.sort(key=lambda x: x['price'] or float('inf'))
    best = products[0] if products else None
    
    return jsonify({
        'query': query,
        'total': len(products),
        'best': best,
        'results': products
    })

@app.route('/history', methods=['GET'])
def history():
    query = request.args.get('q', '')
    items = get_history(query)
    return jsonify([{
        'platform': i.platform,
        'name': i.name,
        'price': i.price,
        'rating': i.rating,
        'url': i.url,
        'image_url': i.image_url,
        'searched_at': str(i.searched_at)
    } for i in items])

if __name__ == '__main__':
    app.run(debug=True, port=5000)