
// cart.js

// --- Globale Funktion zum Laden des Warenkorbs ---
function loadCart(containerId = "cart-items", totalId = "total-price") {
  const container = document.getElementById(containerId);
  const totalPriceEl = document.getElementById(totalId);
  if (!container) return; // Container existiert nicht → nichts tun

  const cart = JSON.parse(localStorage.getItem('cart')) || [];
  container.innerHTML = '';

  if (cart.length === 0) {
    const emptyMsg = document.createElement('p');
    emptyMsg.textContent = 'Dein Warenkorb ist leer.';
    container.appendChild(emptyMsg);
    if (totalPriceEl) totalPriceEl.textContent = '0.00';
    return;
  }

  let total = 0;

  cart.forEach(item => {
    const itemTotal = item.price * item.quantity;
    total += itemTotal;

    const div = document.createElement('div');
    div.className = 'cart-item';

    // Bild
    const img = document.createElement('img');
    img.src = item.image;
    img.alt = item.title;

    // Info-Container
    const info = document.createElement('div');

    // Titel
    const title = document.createElement('strong');
    title.textContent = item.title;

    // Menge
    const qtyControls = document.createElement('span');
    qtyControls.className = 'quantity-controls';

    const decreaseBtn = document.createElement('button');
    decreaseBtn.className = 'quantity-btn';
    decreaseBtn.textContent = '−';
    decreaseBtn.addEventListener('click', () => decreaseQuantity(item.ean, containerId, totalId));

    const qtyText = document.createElement('span');
    qtyText.textContent = ` ${item.quantity} `;

    const increaseBtn = document.createElement('button');
    increaseBtn.className = 'quantity-btn';
    increaseBtn.textContent = '+';
    increaseBtn.addEventListener('click', () => increaseQuantity(item.ean, containerId, totalId));

    qtyControls.appendChild(decreaseBtn);
    qtyControls.appendChild(qtyText);
    qtyControls.appendChild(increaseBtn);

    // Gesamtpreis pro Item
    const priceSpan = document.createElement('span');
    priceSpan.className = 'total-price';
    priceSpan.textContent = `${itemTotal.toFixed(2)} €`;

    // Entfernen-Button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-btn';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => removeFromCart(item.ean, containerId, totalId));

    // Alles zusammenfügen
    info.appendChild(title);
    info.appendChild(qtyControls);
    info.appendChild(priceSpan);
    info.appendChild(removeBtn);

    div.appendChild(img);
    div.appendChild(info);

    container.appendChild(div);
  });

  if (totalPriceEl) totalPriceEl.textContent = total.toFixed(2);
}

// --- Menge erhöhen ---
function increaseQuantity(ean, containerId = "cart-items", totalId = "total-price") {
  const cart = JSON.parse(localStorage.getItem('cart')) || [];
  const item = cart.find(i => i.ean === ean);
  if (item) {
    item.quantity++;
    localStorage.setItem('cart', JSON.stringify(cart));
    loadCart(containerId, totalId);
    updateCartCountIfPossible();
  }
}

// --- Menge verringern ---
function decreaseQuantity(ean, containerId = "cart-items", totalId = "total-price") {
  const cart = JSON.parse(localStorage.getItem('cart')) || [];
  const item = cart.find(i => i.ean === ean);
  if (!item) return;

  if (item.quantity > 1) {
    item.quantity--;
  } else {
    removeFromCart(ean, containerId, totalId);
    return;
  }

  localStorage.setItem('cart', JSON.stringify(cart));
  loadCart(containerId, totalId);
  updateCartCountIfPossible();
}

// --- Item entfernen ---
function removeFromCart(ean, containerId = "cart-items", totalId = "total-price") {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];
  cart = cart.filter(item => item.ean !== ean);
  localStorage.setItem('cart', JSON.stringify(cart));
  loadCart(containerId, totalId);
  updateCartCountIfPossible();
}

// --- Optional: Mini-Cart Count im Elternfenster aktualisieren ---
function updateCartCountIfPossible() {
  if (window.opener && typeof window.opener.updateCartCount === 'function') {
    window.opener.updateCartCount();
  }
}

// --- Checkout-Button Event ---
function setupCheckoutButton(buttonId = "checkout-btn") {
  const checkoutBtn = document.getElementById(buttonId);
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', () => {
      window.location.href = '/checkout'; // Flask Route
    });
  }
}

// --- Automatisch beim Laden der Seite ---
window.addEventListener('DOMContentLoaded', () => {
  loadCart();
  setupCheckoutButton();
});

// --- Optional: global verfügbar machen ---
window.loadCart = loadCart;
window.setupCheckoutButton = setupCheckoutButton;
