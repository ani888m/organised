
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
function addToCart(title, price, image) {
  let cart = JSON.parse(localStorage.getItem('cart')) || [];
  let existing = cart.find(item => item.title === title);

  if (existing) {
    existing.quantity++;
  } else {
    cart.push({ 
      title: title, 
      price: price, 
      quantity: 1, 
      image: image // <- schon fertiger URL-Pfad
    });
  }

  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartCount();
}



// Mobile Menü umschalten
function toggleMobileMenu() {
  const navLinks = document.querySelector('.nav-links');
  const closeBtn = document.querySelector('.close-menu');
  const hamburger = document.querySelector('.mobile-menu');

  if (navLinks) navLinks.classList.toggle('show');
  if (closeBtn) closeBtn.classList.toggle('show');
  if (hamburger) hamburger.classList.toggle('hide'); // <-- Hamburger ausblenden
}

// --- Carousel-Slider ---

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








// --- Produktbilder-Slider (nur für Produktseite) ---
document.addEventListener("DOMContentLoaded", () => {
  const productImages = document.querySelectorAll(".carousel-image");
  const prevBtn = document.querySelector(".product-prev");
  const nextBtn = document.querySelector(".product-next");

  if (productImages.length === 0) return;

  let currentIndex = 0;

  function showImage(index) {
    productImages.forEach((img, i) => {
      img.classList.toggle("active", i === index);
    });
    currentIndex = index;
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const nextIndex = (currentIndex + 1) % productImages.length;
      showImage(nextIndex);
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      const prevIndex = (currentIndex - 1 + productImages.length) % productImages.length;
      showImage(prevIndex);
    });
  }

  showImage(0); // Startbild anzeigen
});

