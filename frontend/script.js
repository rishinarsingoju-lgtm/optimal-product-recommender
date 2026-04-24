const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatLog = document.getElementById("chatLog");
const statusPill = document.getElementById("statusPill");
const resultsTitle = document.getElementById("resultsTitle");
const resultsGrid = document.getElementById("resultsGrid");
const summaryCard = document.getElementById("summaryCard");
const clearButton = document.getElementById("clearButton");

let sessionContext = {};
let lastStructuredQuery = null;

window.addEventListener("resize", () => {
  window.requestAnimationFrame(scrollChatToEnd);
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  addMessage(message, "user");
  chatInput.value = "";

  try {
    setBusy("Thinking");
    const chatResponse = await postJson("/chat", {
      message,
      context: sessionContext,
    });

    sessionContext = chatResponse.context || {};
    lastStructuredQuery = chatResponse.structured_query;
    addMessage(chatResponse.reply, "bot");

    if (chatResponse.ready_to_search) {
      await runSearch(chatResponse.structured_query);
    } else {
      setReady();
    }
  } catch (error) {
    addMessage(error.message || "Something went wrong.", "bot error");
    setReady();
  }
});

clearButton.addEventListener("click", () => {
  sessionContext = {};
  lastStructuredQuery = null;
  chatLog.innerHTML = "";
  addMessage("What are you shopping for?", "bot");
  resultsTitle.textContent = "No search yet";
  resultsGrid.innerHTML = "";
  summaryCard.classList.add("hidden");
  summaryCard.innerHTML = "";
  setReady();
});

async function runSearch(structuredQuery) {
  setBusy("Scraping");
  resultsTitle.textContent = "Searching stores";
  resultsGrid.innerHTML = "";
  summaryCard.classList.add("hidden");

  const searchResponse = await postJson("/search", {
    structured_query: structuredQuery,
    limit: 10,
    sources: ["amazon", "flipkart"],
  });

  if (!searchResponse.products.length) {
    const errorText = searchResponse.errors.length
      ? `I could not scrape results yet: ${searchResponse.errors[0]}`
      : "I could not find products for that query.";
    addMessage(`${errorText} Try a more specific product or budget.`, "bot error");
    resultsTitle.textContent = "No results";
    setReady();
    return;
  }

  setBusy("Ranking");
  const rankResponse = await postJson("/rank", {
    structured_query: structuredQuery,
    products: searchResponse.products,
    limit: 10,
  });

  renderResults(rankResponse.products, structuredQuery);
  addMessage("Done. Here are the best matches.", "bot");
  setReady();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function addMessage(text, className) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${className}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  wrapper.appendChild(paragraph);
  chatLog.appendChild(wrapper);
  scrollChatToEnd();
}

function renderResults(products, structuredQuery) {
  resultsTitle.textContent = resultLabel(structuredQuery);
  resultsGrid.innerHTML = "";

  const [topProduct, ...rest] = products;
  if (topProduct) {
    summaryCard.classList.remove("hidden");
    summaryCard.innerHTML = `
      <div class="summary-image-wrap">
        <img src="${escapeAttr(topProduct.image || "")}" alt="${escapeAttr(topProduct.name)}" class="summary-image" referrerpolicy="no-referrer">
      </div>
      <div class="summary-copy">
        <span class="rank-badge">Top pick</span>
        <h3>${escapeHtml(topProduct.name)}</h3>
        <p>${escapeHtml(topProduct.source)} · ${formatPrice(topProduct.price)} · score ${formatScore(topProduct.score)}</p>
        <div class="summary-actions">
          <a class="preview-link" href="/product/${encodeURIComponent(topProduct.id)}" target="_blank" rel="noopener noreferrer">Preview</a>
          <a class="buy-link" href="${escapeAttr(topProduct.url)}" target="_blank" rel="noopener noreferrer">Buy Now</a>
        </div>
      </div>
    `;
  }

  const renderedProducts = topProduct ? [topProduct, ...rest] : products;
  renderedProducts.forEach((product, index) => {
    resultsGrid.appendChild(createProductCard(product, index + 1));
  });

  scrollChatToEnd();
}

function createProductCard(product, rank) {
  const card = document.createElement("article");
  card.className = "product-card";

  const image = product.image || "";
  const rating = product.rating ? `${Number(product.rating).toFixed(1)}/5` : "No rating";
  const reviews = product.reviews_count ? `${formatNumber(product.reviews_count)} reviews` : "Reviews unavailable";
  const price = formatPrice(product.price);

  card.innerHTML = `
    <div class="product-image-wrap">
      <img class="product-image" src="${escapeAttr(image)}" alt="${escapeAttr(product.name)}" referrerpolicy="no-referrer">
    </div>
    <div class="product-copy">
      <div class="product-row">
        <span class="rank-badge">#${rank}</span>
        <span class="source-chip">${escapeHtml(product.source)}</span>
      </div>
      <h3 class="product-title">${escapeHtml(product.name)}</h3>
      <p class="product-price">${price}</p>
      <div class="product-meta">
        <span>${rating}</span>
        <span>${reviews}</span>
        <span>Score ${formatScore(product.score)}</span>
      </div>
      <div class="product-actions">
        <a class="preview-link" href="/product/${encodeURIComponent(product.id)}" target="_blank" rel="noopener noreferrer">Preview</a>
        <a class="buy-link" href="${escapeAttr(product.url)}" target="_blank" rel="noopener noreferrer">Buy Now</a>
      </div>
    </div>
  `;
  return card;
}

function setBusy(label) {
  statusPill.textContent = label;
  statusPill.classList.add("busy");
  chatInput.disabled = true;
}

function setReady() {
  statusPill.textContent = "Ready";
  statusPill.classList.remove("busy");
  chatInput.disabled = false;
  chatInput.focus();
}

function formatNumber(value) {
  const number = Number(value || 0);
  return number.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function formatPrice(value) {
  if (!value) return "Price unavailable";
  return `INR ${formatNumber(value)}`;
}

function formatScore(value) {
  return Number(value || 0).toFixed(3);
}

function resultLabel(query) {
  const budget = query.budget ? ` up to INR ${formatNumber(query.budget)}` : "";
  if (query.product_type === "phone" && query.brand === "Apple") {
    return `iPhone models${budget}`;
  }
  if (query.product_type === "phone") {
    return `Smartphones${budget}`;
  }
  const brand = query.brand ? `${query.brand} ` : "";
  const product = query.product_type || "products";
  return `${brand}${product}s${budget}`;
}

function escapeHtml(value) {
  return `${value ?? ""}`
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function scrollChatToEnd() {
  chatLog.scrollTop = chatLog.scrollHeight;
}
