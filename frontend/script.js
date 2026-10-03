const API_BASE = "";

let allProducts = [];
let categories = [];

let state = {
    category: "",
    brands: new Set(),
    priceMin: null,
    priceMax: null,
    search: "",
    sort: "relevance",
};

// ---------------------------------------------------------------
// Veri yükleme
// ---------------------------------------------------------------
async function init() {
    const [catRes, prodRes] = await Promise.all([
        fetch(`${API_BASE}/api/categories`),
        fetch(`${API_BASE}/api/products`),
    ]);
    categories = await catRes.json();
    allProducts = await prodRes.json();

    renderCategoryNav();
    renderFilterCategories();
    renderFilterBrands();
    renderFooterCategories();
    applyFiltersAndRender();
}

// ---------------------------------------------------------------
// Üst kategori pilleri
// ---------------------------------------------------------------
function renderCategoryNav() {
    const nav = document.getElementById("category-nav");
    categories.forEach((cat) => {
        const btn = document.createElement("button");
        btn.className = "cat-pill";
        btn.textContent = cat;
        btn.dataset.category = cat;
        btn.addEventListener("click", () => {
            state.category = cat;
            syncCategoryUI();
            applyFiltersAndRender();
        });
        nav.appendChild(btn);
    });
    document.querySelector('.cat-pill[data-category=""]').addEventListener("click", () => {
        state.category = "";
        syncCategoryUI();
        applyFiltersAndRender();
    });
}

function syncCategoryUI() {
    document.querySelectorAll(".cat-pill").forEach((b) => {
        b.classList.toggle("active", b.dataset.category === state.category);
    });
    document.querySelectorAll('#filter-categories input[type="radio"]').forEach((r) => {
        r.checked = r.value === state.category;
    });
}

// ---------------------------------------------------------------
// Sol filtre paneli — alt kategoriler
// ---------------------------------------------------------------
function renderFilterCategories() {
    const box = document.getElementById("filter-categories");
    const counts = {};
    allProducts.forEach((p) => (counts[p.category] = (counts[p.category] || 0) + 1));

    let html = `
      <label class="filter-option">
        <input type="radio" name="filter-cat" value="" checked />
        Tümü <span class="count">${allProducts.length}</span>
      </label>`;
    categories.forEach((cat) => {
        html += `
          <label class="filter-option">
            <input type="radio" name="filter-cat" value="${cat}" />
            ${cat} <span class="count">${counts[cat] || 0}</span>
          </label>`;
    });
    box.innerHTML = html;

    box.querySelectorAll('input[type="radio"]').forEach((radio) => {
        radio.addEventListener("change", (e) => {
            state.category = e.target.value;
            syncCategoryUI();
            applyFiltersAndRender();
        });
    });
}

// ---------------------------------------------------------------
// Sol filtre paneli — marka
// ---------------------------------------------------------------
function renderFilterBrands() {
    const box = document.getElementById("filter-brands");
    const brandCounts = {};
    allProducts.forEach((p) => (brandCounts[p.brand] = (brandCounts[p.brand] || 0) + 1));
    const brands = Object.keys(brandCounts).sort();

    box.innerHTML = brands
        .map(
            (b) => `
        <label class="filter-option">
          <input type="checkbox" value="${b}" />
          ${b} <span class="count">${brandCounts[b]}</span>
        </label>`
        )
        .join("");

    box.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.addEventListener("change", (e) => {
            if (e.target.checked) state.brands.add(e.target.value);
            else state.brands.delete(e.target.value);
            applyFiltersAndRender();
        });
    });
}

// ---------------------------------------------------------------
// Footer kategori linkleri
// ---------------------------------------------------------------
function renderFooterCategories() {
    const box = document.getElementById("footer-categories");
    box.innerHTML = categories.map((c) => `<a href="#">${c}</a>`).join("");
}

// ---------------------------------------------------------------
// Fiyat aralığı + sıfırlama
// ---------------------------------------------------------------
document.getElementById("apply-price").addEventListener("click", () => {
    const min = document.getElementById("price-min").value;
    const max = document.getElementById("price-max").value;
    state.priceMin = min ? Number(min) : null;
    state.priceMax = max ? Number(max) : null;
    applyFiltersAndRender();
});

document.getElementById("reset-filters").addEventListener("click", () => {
    state = { category: "", brands: new Set(), priceMin: null, priceMax: null, search: "", sort: "relevance" };
    document.getElementById("price-min").value = "";
    document.getElementById("price-max").value = "";
    document.getElementById("search-input").value = "";
    document.getElementById("sort-select").value = "relevance";
    document.querySelectorAll('#filter-brands input[type="checkbox"]').forEach((cb) => (cb.checked = false));
    syncCategoryUI();
    applyFiltersAndRender();
});

// ---------------------------------------------------------------
// Arama + sıralama
// ---------------------------------------------------------------
let searchDebounce;
document.getElementById("search-input").addEventListener("input", (e) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
        state.search = e.target.value.trim().toLowerCase();
        applyFiltersAndRender();
    }, 250);
});

document.getElementById("sort-select").addEventListener("change", (e) => {
    state.sort = e.target.value;
    applyFiltersAndRender();
});

// ---------------------------------------------------------------
// Filtreleme + sıralama motoru (istemci tarafında)
// ---------------------------------------------------------------
function applyFiltersAndRender() {
    let result = allProducts.filter((p) => {
        if (state.category && p.category !== state.category) return false;
        if (state.brands.size > 0 && !state.brands.has(p.brand)) return false;
        if (state.priceMin !== null && p.price < state.priceMin) return false;
        if (state.priceMax !== null && p.price > state.priceMax) return false;
        if (state.search) {
            const haystack = `${p.name} ${p.brand} ${p.description || ""} ${p.cpu || ""} ${p.gpu || ""}`.toLowerCase();
            if (!haystack.includes(state.search)) return false;
        }
        return true;
    });

    switch (state.sort) {
        case "price-asc":
            result.sort((a, b) => a.price - b.price);
            break;
        case "price-desc":
            result.sort((a, b) => b.price - a.price);
            break;
        case "stock-desc":
            result.sort((a, b) => b.stock - a.stock);
            break;
        default:
            break; // "relevance" -> orijinal sıra
    }

    renderProducts(result);
}

// ---------------------------------------------------------------
// Ürün grid render
// ---------------------------------------------------------------
function renderProducts(products) {
    const grid = document.getElementById("product-grid");
    document.getElementById("product-count").innerHTML =
        `<b>${products.length}</b> ürün bulundu`;

    if (products.length === 0) {
        grid.innerHTML = '<div class="loading">Bu kriterlere uyan ürün bulunamadı.</div>';
        return;
    }

    grid.innerHTML = products.map(productCardHTML).join("");

    grid.querySelectorAll(".product-card").forEach((card) => {
        card.addEventListener("click", (e) => {
            if (e.target.closest(".btn-add")) return;
            openProductModal(Number(card.dataset.id));
        });
    });
    grid.querySelectorAll(".btn-add").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            quickOrder(Number(btn.dataset.id));
        });
    });
}

function productCardHTML(p) {
    const chips = [];
    if (p.cpu) chips.push(shortSpec(p.cpu));
    if (p.gpu) chips.push(shortSpec(p.gpu));
    if (p.ram_gb) chips.push(`${p.ram_gb}GB ${p.ram_type ? p.ram_type.split("-")[0] : "RAM"}`);
    if (p.storage) chips.push(shortSpec(p.storage));
    if (p.weight_kg) chips.push(`${p.weight_kg}kg`);
    if (p.battery_life_hours) chips.push(`${p.battery_life_hours}sa pil`);

    const stockClass = p.stock > 5 ? "in-stock" : "low-stock";
    const stockLabel = p.stock > 5 ? `stok: ${p.stock}` : `son ${p.stock}`;

    return `
      <div class="product-card" data-id="${p.id}">
        <div class="product-image-box">
          <img
            src="${p.image_url || ''}"
            alt="${p.name}"
            loading="lazy"
            onerror="this.onerror=null; this.closest('.product-image-box').classList.add('no-image'); this.remove();"
          />
        </div>
        <div class="product-card-top">
          <span class="product-category">${p.category} · ${p.brand}</span>
          <span class="stock-badge ${stockClass}">${stockLabel}</span>
        </div>
        <div class="product-name">${p.name}</div>
        <div class="spec-strip">
          ${chips.slice(0, 4).map((c) => `<span class="spec-chip">${c}</span>`).join("")}
        </div>
        <div class="product-footer">
          <div class="product-price">${formatPrice(p.price)}<small>KDV Dahil</small></div>
          <button class="btn-add" data-id="${p.id}">Sepete Ekle</button>
        </div>
      </div>
    `;
}

function shortSpec(text) {
    return text.length > 22 ? text.slice(0, 20) + "…" : text;
}

function formatPrice(price) {
    return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(price);
}

// ---------------------------------------------------------------
// Hızlı sipariş (kart üzerindeki "Sepete Ekle")
// ---------------------------------------------------------------
async function quickOrder(productId) {
    try {
        const res = await fetch(`${API_BASE}/api/orders`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ customer_id: 1, items: [{ product_id: productId, quantity: 1 }] }),
        });
        if (!res.ok) {
            const err = await res.json();
            alert("Sipariş oluşturulamadı: " + err.detail);
            return;
        }
        alert("✔ Siparişiniz alındı!");
        const prodRes = await fetch(`${API_BASE}/api/products`);
        allProducts = await prodRes.json();
        applyFiltersAndRender();
    } catch (e) {
        alert("Sipariş sırasında bir hata oluştu.");
    }
}

// ---------------------------------------------------------------
// Ürün detay modalı + sipariş
// ---------------------------------------------------------------
async function openProductModal(productId) {
    const res = await fetch(`${API_BASE}/api/products/${productId}`);
    const p = await res.json();

    const specRows = [
        ["CPU", p.cpu],
        ["GPU", p.gpu],
        ["RAM", p.ram_gb ? `${p.ram_gb} GB (${p.ram_type || "-"})` : null],
        ["Depolama", p.storage],
        ["Ekran", p.screen],
        ["Ağırlık", p.weight_kg ? `${p.weight_kg} kg` : null],
        ["Pil Ömrü", p.battery_life_hours ? `${p.battery_life_hours} saat` : null],
    ].filter(([, v]) => v);

    document.getElementById("product-modal-content").innerHTML = `
        <div class="modal-image-box">
          <img
            src="${p.image_url || ''}"
            alt="${p.name}"
            onerror="this.onerror=null; this.closest('.modal-image-box').classList.add('no-image'); this.remove();"
          />
        </div>
        <h2>${p.name}</h2>
        <p style="color:var(--ink-muted); font-size:13px; margin-bottom:14px;">${p.description || ""}</p>
        ${specRows.map(([k, v]) => `<div class="spec-row"><b>${k}</b><span>${v}</span></div>`).join("")}
        <div class="spec-row"><b>Fiyat</b><span>${formatPrice(p.price)}</span></div>
        <div class="spec-row"><b>Stok</b><span>${p.stock} adet</span></div>
        <div class="modal-actions">
            <button class="btn-close" onclick="closeModal()">Kapat</button>
            <button class="btn-order" onclick="placeOrder(${p.id})">Sipariş Ver</button>
        </div>
    `;
    document.getElementById("product-modal").classList.add("show");
    document.getElementById("overlay").classList.add("show");
}

function closeModal() {
    document.getElementById("product-modal").classList.remove("show");
    document.getElementById("overlay").classList.remove("show");
}

async function placeOrder(productId) {
    await quickOrder(productId);
    closeModal();
}

// ---------------------------------------------------------------
// AI Asistan Paneli
// ---------------------------------------------------------------
const panel = document.getElementById("assistant-panel");
const overlay = document.getElementById("overlay");
const messagesEl = document.getElementById("assistant-messages");
const form = document.getElementById("assistant-form");
const input = document.getElementById("assistant-input");

document.getElementById("assistant-toggle").addEventListener("click", () => {
    panel.classList.add("open");
    overlay.classList.add("show");
});
document.getElementById("assistant-close").addEventListener("click", closeAssistant);
overlay.addEventListener("click", () => {
    closeAssistant();
    closeModal();
});

function closeAssistant() {
    panel.classList.remove("open");
    overlay.classList.remove("show");
}

document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        input.value = chip.textContent;
        form.dispatchEvent(new Event("submit"));
    });
});

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    appendMessage(question, "user");
    input.value = "";

    const loadingId = appendMessage("Düşünüyorum...", "loading");

    try {
        const res = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });
        const data = await res.json();
        document.getElementById(loadingId).remove();

        if (!res.ok) {
            appendMessage(data.detail || "Bir hata oluştu.", "error");
            return;
        }

        appendBotAnswer(data.answer, data.sources);
    } catch (err) {
        document.getElementById(loadingId).remove();
        appendMessage("Asistana ulaşılamadı. Backend ve Ollama'nın çalıştığından emin olun.", "error");
    }
});

function appendMessage(text, type) {
    const id = "msg-" + Date.now() + Math.random().toString(36).slice(2, 6);
    const div = document.createElement("div");
    div.id = id;
    div.className =
        type === "user" ? "msg msg-user" :
        type === "error" ? "msg msg-error" :
        type === "loading" ? "msg msg-bot msg-loading" : "msg msg-bot";
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return id;
}

function appendBotAnswer(answer, sources) {
    const div = document.createElement("div");
    div.className = "msg msg-bot";
    let html = answer.replace(/\n/g, "<br>");
    if (sources && sources.length) {
        html += `<div class="msg-sources">KAYNAK: ${sources.map((s) => s.name).join(" · ")}</div>`;
    }
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ---------------------------------------------------------------
// Başlat
// ---------------------------------------------------------------
init();
