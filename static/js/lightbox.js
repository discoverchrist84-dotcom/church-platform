/* Click any picture marked data-zoom (or inside formatted text) to see it large. */
(function () {
  "use strict";
  var sel = "img[data-zoom], .rich img";
  var box, img, cap, list = [], idx = 0, lastFocus = null;

  function build() {
    box = document.createElement("div");
    box.className = "lightbox";
    box.hidden = true;
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Picture viewer");
    box.innerHTML =
      '<button type="button" class="lightbox__close" aria-label="Close">&times;</button>' +
      '<button type="button" class="lightbox__nav lightbox__nav--prev" aria-label="Previous picture">&#8249;</button>' +
      '<div class="lightbox__box"><img class="lightbox__img" alt=""><p class="lightbox__cap"></p></div>' +
      '<button type="button" class="lightbox__nav lightbox__nav--next" aria-label="Next picture">&#8250;</button>';
    document.body.appendChild(box);
    img = box.querySelector(".lightbox__img");
    cap = box.querySelector(".lightbox__cap");
    box.addEventListener("click", function (e) {
      if (e.target.closest(".lightbox__close") || e.target === box) close();
      else if (e.target.closest(".lightbox__nav--prev")) step(-1);
      else if (e.target.closest(".lightbox__nav--next")) step(1);
    });
  }

  function show() {
    var el = list[idx];
    img.src = el.currentSrc || el.src;
    img.alt = el.alt || "";
    cap.textContent = el.alt || "";
    cap.hidden = !el.alt;
    var many = list.length > 1;
    box.querySelector(".lightbox__nav--prev").hidden = !many;
    box.querySelector(".lightbox__nav--next").hidden = !many;
  }
  function step(d) { idx = (idx + d + list.length) % list.length; show(); }
  function open(el) {
    if (!box) build();
    var scope = el.closest(".rich") || document;
    list = Array.prototype.slice.call(scope.querySelectorAll(sel));
    if (list.indexOf(el) < 0) list = [el];
    idx = list.indexOf(el);
    lastFocus = document.activeElement;
    box.hidden = false;
    document.body.style.overflow = "hidden";
    show();
    box.querySelector(".lightbox__close").focus();
  }
  function close() {
    box.hidden = true;
    img.removeAttribute("src");
    document.body.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest(sel);
    if (!el || el.closest("a, button, .lightbox")) return;
    e.preventDefault();
    open(el);
  });
  document.addEventListener("keydown", function (e) {
    if (!box || box.hidden) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowLeft") step(-1);
    else if (e.key === "ArrowRight") step(1);
  });
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(sel).forEach(function (el) {
      if (!el.closest("a")) { el.classList.add("zoomable"); el.setAttribute("tabindex", "0"); el.setAttribute("role", "button"); }
    });
  });
  document.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches(sel + ".zoomable") && (!box || box.hidden)) {
      e.preventDefault(); open(e.target);
    }
  });
})();
