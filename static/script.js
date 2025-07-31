    let cartCount = 0;

    function addToCart(bookName, price) {
      cartCount++;
      document.getElementById("cart-count").textContent = cartCount;
      alert(`${bookName} wurde dem Warenkorb hinzugefügt.`);
    }

    function toggleMenu() {
      const navLinks = document.getElementById('nav-links');
      navLinks.classList.toggle('show');
    }
    

    let currentSlide = 0;
const slides = document.querySelectorAll(".carousel-image");

function showSlide(index) {
  slides.forEach((slide, i) => {
    slide.classList.toggle("active", i === index);
  });
}

setInterval(() => {
  currentSlide = (currentSlide + 1) % slides.length;
  showSlide(currentSlide);
}, 4000);

showSlide(currentSlide);


  // Navigation laden
  fetch("nav.html")
    .then(response => response.text())
    .then(data => {
      document.getElementById("nav-placeholder").innerHTML = data;
    });



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



  fetch("newsletter.html")
    .then(res => res.text())
    .then(html => {
      document.getElementById("newsletter-inline").innerHTML = html;
      document.getElementById("newsletter-popup").innerHTML = html;
    });


