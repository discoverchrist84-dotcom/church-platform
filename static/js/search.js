(function () {
  "use strict";
  var input = document.getElementById("q");
  var box = document.getElementById("live-results");
  if (!input || !box) return;

  var timer = null;
  var controller = null;

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function render(items, q) {
    if (!items.length) {
      box.innerHTML = '<p class="muted">No results for “' + esc(q) + "”.</p>";
      return;
    }
    box.innerHTML = items
      .map(function (e) {
        return (
          '<article class="result"><a href="/history/events/' + encodeURIComponent(e.slug) + '/"><strong>' +
          esc(e.title) + '</strong></a> <span class="muted">· ' + esc(e.when) + "</span><p>" +
          esc(e.summary) + "</p></article>"
        );
      })
      .join("");
  }

  input.addEventListener("input", function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < 2) {
      box.innerHTML = "";
      return;
    }
    timer = setTimeout(function () {
      if (controller) controller.abort();
      controller = new AbortController();
      fetch("/api/history/search?q=" + encodeURIComponent(q), { signal: controller.signal })
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (items) { render(items, q); })
        .catch(function (err) { if (err.name !== "AbortError") console.warn(err); });
    }, 250);
  });
})();
