/* Admin: show the picture you just chose, before saving. */
(function () {
  "use strict";
  function human(n) { return n > 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB"; }
  document.addEventListener("change", function (e) {
    var input = e.target;
    if (!input || input.type !== "file") return;
    var box = input.parentNode.querySelector(".upnew");
    if (!box) {
      box = document.createElement("div");
      box.className = "upnew";
      input.parentNode.appendChild(box);
    }
    var file = input.files && input.files[0];
    if (box.firstChild && box._url) { URL.revokeObjectURL(box._url); box._url = null; }
    box.textContent = "";
    if (!file) return;
    if (!/^image\//.test(file.type)) { box.textContent = "Selected: " + file.name + " (" + human(file.size) + ")"; return; }
    var img = document.createElement("img");
    img.className = "apreview";
    box._url = URL.createObjectURL(file);
    img.src = box._url;
    img.alt = "";
    var note = document.createElement("small");
    note.textContent = file.name + " (" + human(file.size) + "). Not saved yet: press Save to keep it. Large photos are resized for you.";
    box.appendChild(img);
    box.appendChild(note);
  });
})();
