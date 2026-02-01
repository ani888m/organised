 function loadCart() {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      let container = document.getElementById('cart-items');
      container.innerHTML = '';

      if (cart.length === 0) {
        container.innerHTML = '<p>Dein Warenkorb ist leer.</p>';
        document.getElementById('total-price').textContent = '0.00';
        return;
      }

      let total = 0;

      cart.forEach(item => {
        let itemTotal = item.price * item.quantity;
        total += itemTotal;

        let div = document.createElement('div');

        div.innerHTML = `
          <img src="${item.image}" alt="${item.title}">
          <div>
            <strong>${item.title}</strong>
            <span class="quantity-controls">
              <button class="quantity-btn" onclick="decreaseQuantity('${item.title}')">−</button>
              &nbsp;${item.quantity}&nbsp;
              <button class="quantity-btn" onclick="increaseQuantity('${item.title}')">+</button>
            </span>
            <span class="total-price">${itemTotal.toFixed(2)} €</span>
            <button class="remove-btn" onclick="removeFromCart('${item.title}')">×</button>
          </div>
        `;

        container.appendChild(div);
      });

      document.getElementById('total-price').textContent = total.toFixed(2);
    }

    function increaseQuantity(title) {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      let item = cart.find(i => i.title === title);
      if (item) {
        item.quantity++;
        localStorage.setItem('cart', JSON.stringify(cart));
        loadCart();
        if (window.opener) {
          window.opener.updateCartCount && window.opener.updateCartCount();
        }
      }
    }

    function decreaseQuantity(title) {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      let item = cart.find(i => i.title === title);
      if (item && item.quantity > 1) {
        item.quantity--;
        localStorage.setItem('cart', JSON.stringify(cart));
        loadCart();
        if (window.opener) {
          window.opener.updateCartCount && window.opener.updateCartCount();
        }
      } else if (item && item.quantity === 1) {
        removeFromCart(title);
      }
    }

    function removeFromCart(title) {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      cart = cart.filter(item => item.title !== title);
      localStorage.setItem('cart', JSON.stringify(cart));
      loadCart();
      if (window.opener) {
        window.opener.updateCartCount && window.opener.updateCartCount();
      }
    }

    window.onload = loadCart;

    document.getElementById('checkout-btn').addEventListener('click', () => {
      window.location.href = '/checkout';
    });
