const categoryFilters = document.querySelectorAll(".filter-category");
const priceFilters = document.querySelectorAll(".filter-price");
const products = document.querySelectorAll(".product-card");
const searchInput = document.getElementById("searchInput");
const minPriceInput = document.getElementById("minPrice");
const maxPriceInput = document.getElementById("maxPrice");
const noResults = document.getElementById("noResults");
function filterProducts() {
  const cats = [...categoryFilters].filter(c=>c.checked).map(c=>c.value);
  const prices = [...priceFilters].filter(p=>p.checked).map(p=>p.value);
  const text = searchInput.value.toLowerCase();
  const minP = minPriceInput.value ? parseInt(minPriceInput.value) : 0;
  const maxP = maxPriceInput.value ? parseInt(maxPriceInput.value) : Infinity;

  let visible = 0;

  products.forEach(p => {
    const name = p.querySelector("h3").innerText.toLowerCase();
    const desc = p.querySelector("p").innerText.toLowerCase();
    const category = p.dataset.category;
    const price = parseInt(p.dataset.price);

    const catMatch = cats.length === 0 || cats.some(c => category.includes(c));
    const checkboxPriceMatch =
      prices.length === 0 || prices.some(r => {
        if (r === "under-999") return price < 1000;
        if (r === "1000-1999") return price >= 1000 && price <= 1999;
        if (r === "premium") return price >= 2000;
      });

    const minMaxMatch = price >= minP && price <= maxP;
    const searchMatch = name.includes(text) || desc.includes(text);

    const show = catMatch && checkboxPriceMatch && minMaxMatch && searchMatch;
    p.style.display = show ? "" : "none";
    if (show) visible++;
  });

  noResults.style.display = visible === 0 ? "block" : "none";
}

/* EVENTS */
[...categoryFilters, ...priceFilters].forEach(cb =>
  cb.addEventListener("change", filterProducts)
);

[searchInput, minPriceInput, maxPriceInput].forEach(el =>
  el.addEventListener("input", filterProducts)
);

document.getElementById("clearFilters").onclick = () => {
  [...categoryFilters, ...priceFilters].forEach(cb => cb.checked = false);
  searchInput.value = "";
  minPriceInput.value = "";
  maxPriceInput.value = "";
  filterProducts();
};

products.forEach(card => {
  card.addEventListener("click", e => {
    if (e.target.tagName === "BUTTON") return;
    window.location.href = card.dataset.link;
  });
});

document.querySelectorAll(".add-to-cart").forEach(btn => {
  btn.onclick = e => {
    e.stopPropagation();
    alert("Added to cart");
  };
});

document.addEventListener("keydown", e => {
  if (e.key === "/") {
    e.preventDefault();
    searchInput.focus();
  }
});