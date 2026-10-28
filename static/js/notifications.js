/* Live notifications over WebSocket: updates the header badge and shows a toast. */
(function () {
  "use strict";
  if (!document.body || document.body.dataset.auth !== "1" || !("WebSocket" in window)) return;

  var badge = document.querySelector("[data-notif-badge]");
  var toasts = document.getElementById("toasts");
  var attempts = 0;
  var MAX_ATTEMPTS = 8;

  function bump() {
    if (!badge) return;
    var n = (parseInt(badge.textContent, 10) || 0) + 1;
    badge.textContent = String(n);
    badge.hidden = false;
  }

  function toast(n) {
    if (!toasts) return;
    var a = document.createElement("a");
    a.className = "toast";
    a.href = n.url || "/notifications/";
    var strong = document.createElement("strong");
    strong.textContent = n.title || "Notification";
    a.appendChild(strong);
    if (n.body) {
      var span = document.createElement("span");
      span.textContent = n.body;
      a.appendChild(span);
    }
    toasts.appendChild(a);
    setTimeout(function () { a.remove(); }, 8000);
  }

  function connect() {
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    var ws;
    try { ws = new WebSocket(proto + location.host + "/ws/notifications/"); } catch (e) { return; }
    ws.onopen = function () { attempts = 0; };
    ws.onmessage = function (ev) {
      var data;
      try { data = JSON.parse(ev.data); } catch (e) { return; }
      bump();
      toast(data);
    };
    ws.onclose = function (ev) {
      if (ev.code === 4401 || ev.code === 4403) return; // not signed in / not allowed
      if (++attempts > MAX_ATTEMPTS) return;
      setTimeout(connect, Math.min(30000, 1000 * Math.pow(2, attempts)));
    };
  }
  connect();
})();
