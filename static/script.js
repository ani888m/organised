// Funktion zum Aktualisieren des Warenkorb-Zählers
function updateCartCount() {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];
  let cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const cartCountElem = document.getElementById("cart-count");
  if (cartCountElem) {
    cartCountElem.textContent = cartCount;
  }
}

// Artikel in den Warenkorb legen und Zähler aktualisieren
function addToCart(bookName, price) {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];

  let existingItem = cart.find(item => item.title === bookName);
  if (existingItem) {
    existingItem.quantity++;
  } else {
    cart.push({ title: bookName, price: price, quantity: 1 });
  }

  localStorage.setItem('cart', JSON.stringify(cart));

  updateCartCount();

  alert(`${bookName} wurde dem Warenkorb hinzugefügt.`);
}

// Mobile Menü umschalten
function toggleMobileMenu() {
  const navLinks = document.querySelector('.nav-links');
  const closeBtn = document.querySelector('.close-menu');

  if (navLinks) navLinks.classList.toggle('show');
  if (closeBtn) closeBtn.classList.toggle('show');
}


// --- Carousel-Slider ---

let currentSlide = 0;

const slides = document.querySelectorAll(".carousel-image");
const nextBtn = document.querySelector(".next");
const prevBtn = document.querySelector(".prev");

function showSlide(index) {
  if (!slides.length) return;

  if (index < 0) index = slides.length - 1;
  if (index >= slides.length) index = 0;

  slides.forEach((slide, i) => {
    slide.classList.toggle("active", i === index);
  });

  currentSlide = index;
}

let slideInterval = setInterval(() => {
  showSlide(currentSlide + 1);
}, 4000);

function resetInterval() {
  clearInterval(slideInterval);
  slideInterval = setInterval(() => {
    showSlide(currentSlide + 1);
  }, 4000);
}

if (nextBtn) {
  nextBtn.addEventListener("click", () => {
    showSlide(currentSlide + 1);
    resetInterval();
  });
}

if (prevBtn) {
  prevBtn.addEventListener("click", () => {
    showSlide(currentSlide - 1);
    resetInterval();
  });
}

// Starte mit dem ersten Slide
showSlide(currentSlide);


// --- Newsletter-Popup ---

window.addEventListener('load', () => {
  const popupShown = localStorage.getItem('newsletterPopupShown');

  if (!popupShown) {
    setTimeout(() => {
      const popup = document.getElementById('newsletter-popup');
      if (popup) {
        popup.classList.remove('popup-hidden');
        localStorage.setItem('newsletterPopupShown', 'true');
      }
    }, 5000);
  }

  // Beim Laden auch den Warenkorb-Zähler aktualisieren
  updateCartCount();
});

// Popup schließen
function closePopup() {
  const popup = document.getElementById('newsletter-popup');
  if (popup) {
    popup.classList.add('popup-hidden');
  }
}

// Newsletter-Snippet dynamisch laden
fetch("/newsletter-snippet")
  .then(res => res.text())
  .then(html => {
    const inline = document.getElementById("newsletter-inline");
    const popup = document.getElementById("newsletter-popup");

    if (inline) inline.innerHTML = html;
    if (popup) popup.innerHTML = html;
  });



function loadCart() {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      let container = document.getElementById('cart-items');
      container.innerHTML = '';

      if(cart.length === 0) {
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
          <strong>${item.title}</strong> - ${item.price.toFixed(2)} € x ${item.quantity} = ${itemTotal.toFixed(2)} €
          <button onclick="removeFromCart('${item.title}')">Entfernen</button>
        `;
        container.appendChild(div);
      });

      document.getElementById('total-price').textContent = total.toFixed(2);
    }

    function removeFromCart(title) {
      let cart = JSON.parse(localStorage.getItem('cart')) || [];
      // Artikel entfernen, dessen Titel mit dem übergebenen übereinstimmt
      cart = cart.filter(item => item.title !== title);
      localStorage.setItem('cart', JSON.stringify(cart));
      loadCart(); // Warenkorb neu laden und anzeigen

      // Optional: auch den Zähler auf der Hauptseite aktualisieren (wenn du dort ein Update willst)
      if (window.opener) {
        window.opener.updateCartCount && window.opener.updateCartCount();
      }
    }

    window.onload = loadCart;

    document.getElementById('checkout-btn').addEventListener('click', () => {
  // Weiterleitung zur Flask-Route /checkout
  window.location.href = '/checkout';
});


