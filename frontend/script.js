// Use the current page origin so the frontend works whether served
// from the Flask backend or opened directly (avoids CORS issues).
const API = window.location.origin || 'http://localhost:5000';
let allResults = [];

async function searchProduct() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  setLoading(true);
  hideError();
  document.getElementById('bestDeal').style.display = 'none';
  document.getElementById('resultsSection').style.display = 'none';

  try {
    const res = await fetch(`${API}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    allResults = data.results;
    renderBest(data.best);
    renderResults(allResults);
  } catch (e) {
    showError('Search failed. Make sure the backend is running. Error: ' + e.message);
  } finally {
    setLoading(false);
  }
}

function renderBest(best) {
  if (!best) return;
  const section = document.getElementById('bestDeal');
  document.getElementById('bestCard').innerHTML = `
    <img src="${best.image_url || 'https://via.placeholder.com/100'}" alt="${best.name}" onerror="this.src='https://via.placeholder.com/100'">
    <div class="info">
      <h3>${best.name}</h3>
      <div class="price">₹${best.price?.toLocaleString()}</div>
      <span class="platform-tag">${best.platform}</span>
      ${best.rating !== 'N/A' ? `<span style="margin-left:8px;font-size:0.8rem;color:var(--muted)">⭐ ${best.rating}</span>` : ''}
      <br><a href="${best.platform === 'Amazon' ? (() => {
        let url = `https://www.amazon.in/s?k=${encodeURIComponent(best.name)}`;
        if (best.price) {
          const amt = Math.round(best.price * 100);
          url += `&rh=p_36%3A${amt}-${amt}`;
        }
        return url;
      })() : best.url}" target="_blank" style="color:var(--accent2);font-size:0.85rem;margin-top:8px;display:inline-block;">View on ${best.platform} →</a>
    </div>
  `;
  section.style.display = 'block';
}

function renderResults(products) {
  const grid = document.getElementById('resultsGrid');
  document.getElementById('resultCount'). textContent = `(${products.length} found)`;

  grid.innerHTML = products.map(p => `
    <div class="product-card">
      <div class="img-wrap">
        <img src="${p.image_url || ''}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/150'">
      </div>
      <div class="card-body">
        <div class="card-platform">${p.platform}</div>
        <div class="card-name">${p.name}</div>
        <div class="card-price">₹${p.price?.toLocaleString() || 'N/A'}</div>
        <div class="card-rating">⭐ ${p.rating}</div>
        <a href="${p.platform === 'Amazon' ? (() => {
          let url = `https://www.amazon.in/s?k=${encodeURIComponent(p.name)}`;
          if (p.price) {
            const amt = Math.round(p.price * 100);
            url += `&rh=p_36%3A${amt}-${amt}`;
          }
          return url;
        })() : p.url}" target="_blank" class="card-btn">View Deal</a>
      </div>
    </div>
  `).join('');

  document.getElementById('resultsSection').style.display = 'block';
}

function sortResults(mode) {
  let sorted = [...allResults];
  if (mode === 'price_asc') sorted.sort((a,b) => (a.price||999999) - (b.price||999999));
  else if (mode === 'price_desc') sorted.sort((a,b) => (b.price||0) - (a.price||0));
  else if (mode === 'rating') sorted.sort((a,b) => parseFloat(b.rating)||0 - parseFloat(a.rating)||0);
  renderResults(sorted);
}

function setLoading(on) {
  const btn = document.getElementById('searchBtn');
  btn.querySelector('.btn-text').style.display = on ? 'none' : '';
  btn.querySelector('.btn-loader').style.display = on ? '' : '  none';
  btn.disabled = on;
  if (on) {
    document.getElementById('resultsGrid').innerHTML = `
      <div class="loading-state" style="grid-column:1/-1">
        <div class="spinner"></div>Searching across platforms...
      </div>`;
    document.getElementById('resultsSection').style.display = 'block';
  }
}

function showError(msg) { const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }
function hideError() { document.getElementById('error').style.display = 'none'; }

document.getElementById('searchInput').addEventListener('keypress', e => {
  if (e.key === 'Enter') searchProduct();
});