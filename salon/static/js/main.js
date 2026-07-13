// Mobile menu toggle
const menuToggle = document.getElementById("menuToggle");
const mobileMenu = document.getElementById("mobileMenu");
if (menuToggle && mobileMenu) {
  menuToggle.addEventListener("click", () => {
    mobileMenu.classList.toggle("open");
  });
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener("click", function (e) {
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

// Animate elements on scroll
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
      }
    });
  },
  { threshold: 0.1 }
);

document.querySelectorAll(".category-card, .feature-card, .service-card").forEach(el => {
  el.style.opacity = "0";
  el.style.transform = "translateY(20px)";
  el.style.transition = "opacity 0.5s ease, transform 0.5s ease";
  observer.observe(el);
});

// Footer website feedback
const feedbackToggle = document.getElementById("feedbackToggle");
const feedbackForm = document.getElementById("feedbackForm");
const feedbackStatus = document.getElementById("feedbackStatus");
const feedbackSubmittedAt = document.getElementById("feedbackSubmittedAt");

if (feedbackToggle && feedbackForm && feedbackStatus) {
  const ratingInputs = feedbackForm.querySelectorAll('input[name="rating"]');
  const ratingLabels = feedbackForm.querySelectorAll(".footer-rating-options label");
  const submitButton = feedbackForm.querySelector('button[type="submit"]');

  const displayRating = value => {
    ratingLabels.forEach(label => {
      label.classList.toggle(
        "active",
        Number(label.dataset.rating) <= Number(value),
      );
    });
  };

  ratingInputs.forEach(input => {
    input.addEventListener("change", () => {
      displayRating(input.value);
    });
  });

  feedbackToggle.addEventListener("click", () => {
    const isOpen = !feedbackForm.hidden;
    feedbackForm.hidden = isOpen;
    feedbackToggle.setAttribute("aria-expanded", String(!isOpen));

    if (!isOpen) {
      feedbackStatus.textContent = "";
      feedbackStatus.className = "footer-feedback-status";
      ratingInputs[0]?.focus();
    }
  });

  feedbackForm.addEventListener("submit", async event => {
    event.preventDefault();

    if (!feedbackForm.reportValidity()) {
      return;
    }

    if (feedbackSubmittedAt) {
      feedbackSubmittedAt.value = new Date().toISOString();
    }

    feedbackStatus.textContent = "";
    feedbackStatus.className = "footer-feedback-status";
    submitButton.disabled = true;

    try {
      const response = await fetch(feedbackForm.action, {
        method: "POST",
        body: new FormData(feedbackForm),
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      const result = await response.json();

      feedbackStatus.textContent = result.message;
      feedbackStatus.classList.add(result.success ? "success" : "error");

      if (result.success) {
        feedbackForm.reset();
        displayRating(0);
        feedbackForm.hidden = true;
        feedbackToggle.setAttribute("aria-expanded", "false");
      }
    } catch (error) {
      feedbackStatus.textContent = feedbackForm.dataset.networkError;
      feedbackStatus.classList.add("error");
    } finally {
      submitButton.disabled = false;
    }
  });
}
