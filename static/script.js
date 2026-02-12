// -----------------------------
// Helper für Cookies (optional für späteres Tracking)
// -----------------------------
function setCookie(name, value, days) {
  let expires = "";
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie = name + "=" + encodeURIComponent(value) + expires + "; path=/; Secure; SameSite=Lax";
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

// -----------------------------
// Warenkorb-Funktionen (technisch notwendig, DSGVO-konform)
// -----------------------------
function updateCartCount() {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];
  let cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const cartCountElem = document.getElementById("cart-count");
  if (cartCountElem) cartCountElem.textContent = cartCount;

  // Optional: auch als Cookie speichern, falls serverseitig genutzt werden soll
  // setCookie("cart", JSON.stringify(cart), 7); // 7 Tage
}

function addToCart(title, price, image, ean) {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];

  let existing = cart.find(item => item.ean === ean);

  if (existing) {
    existing.quantity++;
  } else {
    cart.push({ title, price, quantity: 1, image, ean });
  }

  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartCount();
}


// -----------------------------
// Mobile Menü
// -----------------------------
function toggleMobileMenu() {
  const navLinks = document.querySelector('.nav-links');
  const closeBtn = document.querySelector('.close-menu');
  const hamburger = document.querySelector('.mobile-menu');

  if (navLinks) navLinks.classList.toggle('show');
  if (closeBtn) closeBtn.classList.toggle('show');
  if (hamburger) hamburger.classList.toggle('hide');
}

// -----------------------------
// Carousel-Slider
// -----------------------------
let currentSlide = 0;
const slides = document.querySelectorAll(".carousel-slide");
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

let slideInterval = setInterval(() => showSlide(currentSlide + 1), 4000);

function resetInterval() {
  clearInterval(slideInterval);
  slideInterval = setInterval(() => showSlide(currentSlide + 1), 4000);
}

if (nextBtn) nextBtn.addEventListener("click", () => { showSlide(currentSlide + 1); resetInterval(); });
if (prevBtn) prevBtn.addEventListener("click", () => { showSlide(currentSlide - 1); resetInterval(); });

showSlide(currentSlide);

// -----------------------------
// Produktbilder-Slider (Produktseite)
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
  const productImages = document.querySelectorAll(".carousel-image");
  const prevBtn = document.querySelector(".product-prev");
  const nextBtn = document.querySelector(".product-next");

  if (productImages.length === 0) return;

  let currentIndex = 0;

  function showImage(index) {
    productImages.forEach((img, i) => img.classList.toggle("active", i === index));
    currentIndex = index;
  }

  if (nextBtn) nextBtn.addEventListener("click", () => {
    showImage((currentIndex + 1) % productImages.length);
  });

  if (prevBtn) prevBtn.addEventListener("click", () => {
    showImage((currentIndex - 1 + productImages.length) % productImages.length);
  });

  showImage(0);
});

// -----------------------------
// Header scroll-Effekt
// -----------------------------
window.addEventListener("scroll", () => {
  const header = document.querySelector("header");
  if (window.scrollY > 50) header.classList.add("shrink");
  else header.classList.remove("shrink");
});

// -----------------------------
// Beim Laden: Warenkorb-Zähler aktualisieren
// -----------------------------
window.addEventListener('load', updateCartCount);


function toggleInfoDetails() {
  const box = document.querySelector('.info-details');
  box.classList.toggle('info-open');
}

document.addEventListener("DOMContentLoaded", function () {

  const categories = document.querySelectorAll(".category");
  const button = document.getElementById("showMoreBtn");

  let visibleCount = 3; // wie viele Kategorien pro Klick gezeigt werden

  function updateCategories() {
    categories.forEach((cat, index) => {
      cat.style.display = index < visibleCount ? "block" : "none";
    });

    // Button ausblenden, wenn alle Kategorien sichtbar sind
    if (visibleCount >= categories.length) {
      button.style.display = "none";
    } else {
      button.style.display = "inline-block";
    }
  }

  // Beim Laden erste Kategorien anzeigen
  updateCategories();

  // Klick auf den Button
  button.addEventListener("click", () => {
    visibleCount += 3; // nächste 3 Kategorien anzeigen
    updateCategories();
  });

});


