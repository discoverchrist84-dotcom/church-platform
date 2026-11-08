(function () {
  "use strict";

  var root = document.documentElement;

  // --- Theme: light / dark / follow device ------------------------------
  function storedTheme() {
    try { return localStorage.getItem("theme") || "system"; } catch (e) { return "system"; }
  }
  function applyTheme(choice) {
    if (choice === "light" || choice === "dark") root.setAttribute("data-theme", choice);
    else root.removeAttribute("data-theme");
    document.querySelectorAll("[data-theme-choice]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(btn.dataset.themeChoice === choice));
    });
  }
  applyTheme(storedTheme());
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-theme-choice]");
    if (!btn) return;
    var choice = btn.dataset.themeChoice;
    try {
      if (choice === "system") localStorage.removeItem("theme");
      else localStorage.setItem("theme", choice);
    } catch (err) { /* private mode: still apply for this visit */ }
    applyTheme(choice);
  });

  // --- Mobile nav drawer -------------------------------------------------
  // Menu groups (Church, My account) close when you click elsewhere or press Esc.
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.navdrop[open]").forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.querySelectorAll("details.navdrop[open]").forEach(function (d) { d.removeAttribute("open"); });
  });

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("nav");
  function setNav(open) {
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }
  if (toggle && nav) {
    toggle.addEventListener("click", function () { setNav(!nav.classList.contains("open")); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setNav(false); });
    nav.addEventListener("click", function (e) { if (e.target.closest("a")) setNav(false); });
    var wide = window.matchMedia("(min-width: 62rem)");
    var onWide = function (m) { if (m.matches) setNav(false); };
    if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
  }

  // --- Reveal-on-scroll --------------------------------------------------
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // --- Service worker (offline support + installability) -----------------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(function (err) {
        console.warn("Service worker registration failed:", err);
      });
    });
  }

  // --- Install button (Chrome/Edge/Android) ------------------------------
  var deferredPrompt = null;
  var installBtn = document.getElementById("install-btn");
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) installBtn.hidden = false;
  });
  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        installBtn.hidden = true;
      });
    });
  }
  window.addEventListener("appinstalled", function () { if (installBtn) installBtn.hidden = true; });

  // iOS Safari has no install prompt: show a hint instead.
  var isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  var hint = document.getElementById("ios-hint");
  if (hint && isIos && !standalone) hint.hidden = false;

  // --- JSON API helpers --------------------------------------------------
  function getCookie(name) {
    var match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match[2]) : "";
  }

  // --- Join branch -------------------------------------------------------
  var joinBtn = document.getElementById("join-btn");
  if (joinBtn) {
    joinBtn.addEventListener("click", function () {
      joinBtn.disabled = true;
      fetch("/api/branches/" + encodeURIComponent(joinBtn.dataset.slug) + "/join", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          window.location.reload();
        })
        .catch(function () {
          joinBtn.disabled = false;
          alert("Sorry, we couldn't add you to this branch. Please try again.");
        });
    });
  }

  // --- Giving: pick a preset amount -------------------------------------
  var custom = document.getElementById("id_amount");
  document.querySelectorAll(".chips input[name=preset]").forEach(function (r) {
    r.addEventListener("change", function () { if (custom) custom.value = r.value; });
  });

  // --- Motion niceties (all skipped for people who prefer reduced motion) ----
  var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Staggered reveal: give siblings a small delay so they cascade in.
  document.querySelectorAll(".features, .cards, .grid, .events, .branches").forEach(function (group) {
    Array.prototype.forEach.call(group.querySelectorAll(":scope > .reveal"), function (el, i) {
      el.style.setProperty("--d", Math.min(i, 8) * 80 + "ms");
    });
  });

  var header = document.querySelector(".site-header");
  var toTop = document.getElementById("to-top");
  var bar = document.getElementById("progress");
  var ticking = false;
  function onScroll() {
    var y = window.pageYOffset || root.scrollTop;
    var max = root.scrollHeight - window.innerHeight;
    if (header) header.classList.toggle("scrolled", y > 24);
    if (toTop) toTop.classList.toggle("show", y > 600);
    if (bar && !calm) bar.style.transform = "scaleX(" + (max > 0 ? Math.min(y / max, 1) : 0) + ")";
    if (!calm) {
      var hero = document.querySelector(".hero");
      if (hero && y < window.innerHeight) {
        hero.style.setProperty("--py", (y * 0.25).toFixed(1) + "px");
      }
    }
    ticking = false;
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();
  if (toTop) toTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
  });

  // Button ripple from the point of touch/click.
  document.addEventListener("pointerdown", function (e) {
    if (calm) return;
    var btn = e.target.closest(".btn");
    if (!btn) return;
    var r = btn.getBoundingClientRect();
    var dot = document.createElement("span");
    dot.className = "ripple";
    dot.style.left = e.clientX - r.left + "px";
    dot.style.top = e.clientY - r.top + "px";
    btn.appendChild(dot);
    setTimeout(function () { dot.remove(); }, 700);
  });

  // Cards lean toward the pointer on mouse devices.
  if (!calm && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.querySelectorAll("a.card.feature").forEach(function (card) {
      card.classList.add("tilt");
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        card.style.setProperty("--ry", ((e.clientX - r.left) / r.width - 0.5) * 8 + "deg");
        card.style.setProperty("--rx", (0.5 - (e.clientY - r.top) / r.height) * 8 + "deg");
      });
      card.addEventListener("pointerleave", function () {
        card.style.removeProperty("--rx"); card.style.removeProperty("--ry");
      });
    });
  }

  // Fade the page out just before navigating (same-origin links only).
  document.addEventListener("click", function (e) {
    if (calm || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest("a[href]");
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
    var url;
    try { url = new URL(a.href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin || url.pathname === location.pathname && url.hash) return;
    root.classList.add("leaving");
  });
  // Coming back with the Back button must not leave the page faded out.
  window.addEventListener("pageshow", function () { root.classList.remove("leaving"); });

  // Briefly animate the colour change when the theme is switched.
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-theme-choice]") || calm) return;
    root.classList.add("theming");
    setTimeout(function () { root.classList.remove("theming"); }, 450);
  });

  // Show a spinner on a form's submit button so a slow tap doesn't look frozen.
  document.addEventListener("submit", function (e) {
    var btn = e.target.querySelector && e.target.querySelector("button[type=submit], button:not([type])");
    if (btn && !e.defaultPrevented) {
      setTimeout(function () { btn.disabled = true; btn.classList.add("busy"); }, 0);
    }
  });
  window.addEventListener("pageshow", function (ev) {
    if (!ev.persisted) return;
    document.querySelectorAll("button.busy").forEach(function (b) { b.disabled = false; b.classList.remove("busy"); });
  });

  // Images fade in when they have loaded.
  document.querySelectorAll("main img").forEach(function (img) {
    if (img.classList.contains("hero__logo")) return;
    if (img.complete) return;
    img.classList.add("fade");
    img.addEventListener("load", function () { img.classList.add("loaded"); });
    img.addEventListener("error", function () { img.classList.add("loaded"); });
    setTimeout(function () { img.classList.add("loaded"); }, 3000); // safety net: an image is never left invisible
  });

  // --- Show / hide password -------------------------------------------------
  var EYE = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 19C5 19 1 12 1 12a19.7 19.7 0 0 1 5.06-5.94M9.9 4.24A10.9 10.9 0 0 1 12 5c7 0 11 7 11 7a19.6 19.6 0 0 1-3.17 4.19M14.12 14.12a3 3 0 1 1-4.24-4.24"/><path d="M1 1l22 22"/></svg>';
  document.querySelectorAll("input[type=password]").forEach(function (input) {
    var wrap = document.createElement("span");
    wrap.className = "pw";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pw__toggle";
    btn.setAttribute("aria-pressed", "false");
    btn.setAttribute("aria-label", "Show password");
    btn.innerHTML = EYE;
    wrap.appendChild(btn);
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-pressed", String(show));
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      btn.innerHTML = show ? EYE_OFF : EYE;
      input.focus();
    });
    // Never leave a password visible if the browser restores the page from its back/forward cache.
    window.addEventListener("pageshow", function () {
      input.type = "password"; btn.setAttribute("aria-pressed", "false"); btn.innerHTML = EYE;
    });
  });

  // --- Filters that apply as soon as a dropdown changes -----------------------
  document.querySelectorAll("form[data-autosubmit] select").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });

  // --- Count-up numbers (landing page stats) ----------------------------------
  var counters = document.querySelectorAll("[data-count]");
  function runCount(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    if (calm || target < 2) { el.textContent = target.toLocaleString(); return; }
    var start = null, dur = 1400;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min((ts - start) / dur, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3))).toLocaleString();
      if (t < 1) window.requestAnimationFrame(step);
    }
    window.requestAnimationFrame(step);
  }
  if ("IntersectionObserver" in window && counters.length) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { runCount(en.target); co.unobserve(en.target); } });
    }, { threshold: 0.4 });
    counters.forEach(function (el) { el.textContent = "0"; co.observe(el); });
  } else {
    counters.forEach(runCount);
  }
})();
