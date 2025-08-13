// --- Hilfsfunktionen ---
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// --- Warenkorb ---
function updateCartCount() {
  const cart = JSON.parse(localStorage.getItem('cart') || '[]');
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  const elem = $("#cart-count");
  if (elem) elem.textContent = count;
}

function addToCart(title, price, image) {
  const cart = JSON.parse(localStorage.getItem('cart') || '[]');
  const existing = cart.find(item => item.title === title);

  if (existing) existing.quantity++;
  else cart.push({ title, price, quantity: 1, image });

  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartCount();
}

// --- Mobile Menü ---
function toggleMobileMenu() {
  const navLinks = $(".nav-links");
  const hamburger = $(".hamburger-menu");
  const closeIcon = $(".close-menu");

  navLinks?.classList.toggle("show");

  if (closeIcon && hamburger) {
    // Wenn Menü offen, Hamburger ausblenden, Kreuz einblenden
    const isOpen = navLinks.classList.contains("show");
    hamburger.classList.toggle("hide", isOpen); // hide = true wenn offen
    closeIcon.classList.toggle("hide", !isOpen); // hide = false wenn offen
  }
}


// --- Carousel ---
const slides = $$(".carousel-image");
let currentSlide = 0;
let slideInterval;

function showSlide(index) {
  if (!slides.length) return;
  currentSlide = (index + slides.length) % slides.length;
  slides.forEach((s, i) => s.classList.toggle("active", i === currentSlide));
}

function resetSlideInterval() {
  clearInterval(slideInterval);
  slideInterval = setInterval(() => showSlide(currentSlide + 1), 4000);
}

$(".next")?.addEventListener("click", () => { showSlide(currentSlide + 1); resetSlideInterval(); });
$(".prev")?.addEventListener("click", () => { showSlide(currentSlide - 1); resetSlideInterval(); });

slideInterval = setInterval(() => showSlide(currentSlide + 1), 4000);
showSlide(currentSlide);

// --- Newsletter Popup ---
function showPopup() {
  const popup = $("#newsletter-popup");
  if (popup) popup.classList.remove("popup-hidden");
  localStorage.setItem('newsletterPopupShown', 'true');
}

function closePopup() {
  $("#newsletter-popup")?.classList.add("popup-hidden");
}

window.addEventListener("load", () => {
  if (!localStorage.getItem('newsletterPopupShown')) setTimeout(showPopup, 5000);
  updateCartCount();
});

// --- Newsletter Snippet ---
fetch("/newsletter-snippet")
  .then(res => res.text())
  .then(html => {
    if ($("#newsletter-inline")) $("#newsletter-inline").innerHTML = html;
    if ($("#newsletter-popup")) $("#newsletter-popup").innerHTML = html;
  });
