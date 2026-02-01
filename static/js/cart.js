 // cart.js

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('cart-items');
  const totalPriceEl = document.getElementById('total-price');
  const checkoutBtn = document.getElementById('checkout-btn');

  // Lade den Warenkorb beim Laden der Seite
  loadCart();

  // Checkout-Button Event
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', () => {
      window.location.href = '/templates/checkout';
    });
  }

  // --- Funktionen ---

  function loadCart() {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    container.innerHTML = '';

    if (cart.length === 0) {
      container.textContent = '';
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
      decreaseBtn.addEventListener('click', () => decreaseQuantity(item.title));

      const qtyText = document.createElement('span');
      qtyText.textContent = ` ${item.quantity} `;

      const increaseBtn = document.createElement('button');
      increaseBtn.className = 'quantity-btn';
      increaseBtn.textContent = '+';
      increaseBtn.addEventListener('click', () => increaseQuantity(item.title));

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
      removeBtn.addEventListener('click', () => removeFromCart(item.title));

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

  function increaseQuantity(title) {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const item = cart.find(i => i.title === title);
    if (item) {
      item.quantity++;
      localStorage.setItem('cart', JSON.stringify(cart));
      loadCart();
      updateCartCountIfPossible();
    }
  }

  function decreaseQuantity(title) {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const item = cart.find(i => i.title === title);
    if (item) {
      if (item.quantity > 1) {
        item.quantity--;
      } else {
        // Menge 1 => entfernen
        removeFromCart(title);
        return;
      }
      localStorage.setItem('cart', JSON.stringify(cart));
      loadCart();
      updateCartCountIfPossible();
    }
  }

  function removeFromCart(title) {
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    cart = cart.filter(item => item.title !== title);
    localStorage.setItem('cart', JSON.stringify(cart));
    loadCart();
    updateCartCountIfPossible();
  }

  // Optional: Aktualisiere Cart Count im Elternfenster
  function updateCartCountIfPossible() {
    if (window.opener && typeof window.opener.updateCartCount === 'function') {
      window.opener.updateCartCount();
    }
  }
});
