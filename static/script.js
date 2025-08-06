    let cartCount = 0;

    function addToCart(bookName, price) {
      cartCount++;
      document.getElementById("cart-count").textContent = cartCount;
      alert(`${bookName} wurde dem Warenkorb hinzugefügt.`);
    }

    

function toggleMobileMenu() {
  const navLinks = document.querySelector('.nav-links');
  const closeBtn = document.querySelector('.close-menu');

  navLinks.classList.toggle('show');
  closeBtn.classList.toggle('show'); // optional, falls du separat steuern willst
}


   let currentSlide = 0;

// ✅ Diese drei Zeilen haben bei dir gefehlt!
const slides = document.querySelectorAll(".carousel-image");
const nextBtn = document.querySelector(".next");
const prevBtn = document.querySelector(".prev");

function showSlide(index) {
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

nextBtn.addEventListener("click", () => {
  showSlide(currentSlide + 1);
  resetInterval();
});

prevBtn.addEventListener("click", () => {
  showSlide(currentSlide - 1);
  resetInterval();
});

// 🚀 Starte mit erstem Slide
showSlide(currentSlide);


showSlide(currentSlide);

showSlide(currentSlide);





// Popup automatisch nach 5 Sekunden anzeigen

window.addEventListener('load', () => {
  // Prüfen, ob das Popup schon angezeigt wurde
  const popupShown = localStorage.getItem('newsletterPopupShown');

  if (!popupShown) {
    // Nach 5 Sekunden anzeigen
    setTimeout(() => {
      document.getElementById('newsletter-popup').classList.remove('popup-hidden');
      localStorage.setItem('newsletterPopupShown', 'true'); // Merken, dass es gezeigt wurde
    }, 5000);
  }
});


  function closePopup() {
    document.getElementById('newsletter-popup').classList.add('popup-hidden');
  }





fetch("/newsletter-snippet")
  .then(res => res.text())
  .then(html => {
    document.getElementById("newsletter-inline").innerHTML = html;
    document.getElementById("newsletter-popup").innerHTML = html;
  });


