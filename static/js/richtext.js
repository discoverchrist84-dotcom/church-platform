/* A small, dependency-free rich text editor for the admin.
   Turns every <textarea class="js-rich"> into a toolbar + editable page. The HTML is cleaned again on the server. */
(function () {
  "use strict";
  var COLORS = ["#0b2a5b", "#1d5fd6", "#0a7a3b", "#b3261e", "#c47f00", "#6a3fb5", "#111111", "#666666"];
  var HILITES = ["#fff3b0", "#c8f2d4", "#cfe3ff", "#ffd6d2", "transparent"];

  function btn(label, title, action, extra) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "rt-btn" + (extra ? " " + extra : ""); b.title = title; b.innerHTML = label;
    b.addEventListener("mousedown", function (e) { e.preventDefault(); }); // keep the selection in the page
    b.addEventListener("click", action);
    return b;
  }
  function sep() { var s = document.createElement("span"); s.className = "rt-sep"; return s; }
  function csrf(form) { var i = form && form.querySelector("input[name=csrfmiddlewaretoken]"); return i ? i.value : ""; }

  function build(ta) {
    var form = ta.form, wrap = document.createElement("div"), bar = document.createElement("div"), page = document.createElement("div");
    var source = document.createElement("textarea"), imgbar = document.createElement("div"), status = document.createElement("div");
    wrap.className = "rt"; bar.className = "rt-bar"; page.className = "rt-page rich"; page.contentEditable = "true"; page.spellcheck = true;
    source.className = "rt-source"; source.hidden = true; imgbar.className = "rt-imgbar"; imgbar.hidden = true; status.className = "rt-status";
    page.innerHTML = ta.value || "";
    if (page.innerHTML && !/<\s*(p|h[1-6]|ul|ol|div|blockquote|img|br)\b/i.test(page.innerHTML)) {
      page.innerHTML = page.innerHTML.split(/\n\s*\n/).map(function (t) { return "<p>" + t.replace(/\n/g, "<br>") + "</p>"; }).join("");
    }
    var selected = null;

    function exec(cmd, val) { page.focus(); document.execCommand(cmd, false, val || null); sync(); }
    function sync() { ta.value = source.hidden ? page.innerHTML : source.value; }
    function block(tag) { exec("formatBlock", "<" + tag + ">"); }

    var block_sel = document.createElement("select");
    block_sel.className = "rt-select"; block_sel.title = "Paragraph style";
    [["p", "Paragraph"], ["h2", "Heading"], ["h3", "Sub-heading"], ["h4", "Small heading"], ["blockquote", "Quote"]].forEach(function (o) {
      var op = document.createElement("option"); op.value = o[0]; op.textContent = o[1]; block_sel.appendChild(op);
    });
    block_sel.addEventListener("change", function () { block(block_sel.value); });
    var size_sel = document.createElement("select");
    size_sel.className = "rt-select"; size_sel.title = "Text size";
    [["3", "Normal size"], ["2", "Small"], ["4", "Large"], ["5", "Larger"], ["6", "Huge"]].forEach(function (o) {
      var op = document.createElement("option"); op.value = o[0]; op.textContent = o[1]; size_sel.appendChild(op);
    });
    size_sel.addEventListener("change", function () { exec("fontSize", size_sel.value); });

    function swatches(title, list, cmd) {
      var d = document.createElement("span"); d.className = "rt-sw"; d.title = title;
      var t = document.createElement("span"); t.className = "rt-sw__t"; t.textContent = title === "Text colour" ? "A" : "▮"; d.appendChild(t);
      var m = document.createElement("span"); m.className = "rt-sw__menu";
      list.forEach(function (c) {
        var s = document.createElement("button"); s.type = "button"; s.className = "rt-dot"; s.style.background = c === "transparent" ? "#fff" : c;
        s.title = c === "transparent" ? "No highlight" : c; if (c === "transparent") s.textContent = "×";
        s.addEventListener("mousedown", function (e) { e.preventDefault(); });
        s.addEventListener("click", function () { exec(cmd, c); m.parentNode.classList.remove("open"); });
        m.appendChild(s);
      });
      d.appendChild(m);
      t.addEventListener("mousedown", function (e) { e.preventDefault(); d.classList.toggle("open"); });
      return d;
    }

    function addLink() {
      var url = window.prompt("Link address (start with https://, or / for a page on this site):", "https://");
      if (url && url !== "https://") exec("createLink", url);
    }
    function upload(file) {
      if (!file || !/^image\//.test(file.type)) { window.alert("Please choose a picture (JPG, PNG, WEBP or GIF)."); return; }
      status.textContent = "Uploading picture…";
      var fd = new FormData(); fd.append("image", file);
      fetch(ta.getAttribute("data-upload-url"), { method: "POST", body: fd, headers: { "X-CSRFToken": csrf(form) }, credentials: "same-origin" })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok) throw new Error(res.j.error || "Upload failed");
          page.focus();
          document.execCommand("insertHTML", false, '<img src="' + res.j.url + '" alt="' + (file.name || "").replace(/\.[^.]+$/, "").replace(/["<>]/g, "") + '" class="img-center">');
          status.textContent = "Picture added. Click it to choose where it sits and how big it is.";
          sync();
        })
        .catch(function (e) { status.textContent = ""; window.alert(e.message || "The picture could not be uploaded."); });
    }
    var file = document.createElement("input"); file.type = "file"; file.accept = "image/*"; file.hidden = true;
    file.addEventListener("change", function () { upload(file.files[0]); file.value = ""; });

    function toggleSource() {
      if (source.hidden) { source.value = page.innerHTML; source.hidden = false; page.hidden = true; imgbar.hidden = true; }
      else { page.innerHTML = source.value; source.hidden = true; page.hidden = false; }
      sync();
    }

    [
      block_sel, size_sel, sep(),
      btn("<b>B</b>", "Bold (Ctrl+B)", function () { exec("bold"); }),
      btn("<i>I</i>", "Italic (Ctrl+I)", function () { exec("italic"); }),
      btn("<u>U</u>", "Underline (Ctrl+U)", function () { exec("underline"); }),
      btn("<s>S</s>", "Strike-through", function () { exec("strikeThrough"); }),
      btn("x<sup>2</sup>", "Superscript", function () { exec("superscript"); }),
      sep(), swatches("Text colour", COLORS, "foreColor"), swatches("Highlight", HILITES, "hiliteColor"), sep(),
      btn("&#8226;&#8801;", "Bullet list", function () { exec("insertUnorderedList"); }),
      btn("1.&#8801;", "Numbered list", function () { exec("insertOrderedList"); }),
      btn("&#8676;", "Align left", function () { exec("justifyLeft"); }),
      btn("&#8801;", "Centre", function () { exec("justifyCenter"); }),
      btn("&#8677;", "Align right", function () { exec("justifyRight"); }),
      btn("&#9776;", "Justify", function () { exec("justifyFull"); }),
      sep(),
      btn("&#128279;", "Add a link", addLink), btn("&#10006;&#128279;", "Remove link", function () { exec("unlink"); }),
      btn("&#128247; Picture", "Add a picture", function () { file.click(); }, "rt-wide"),
      btn("&#8212;", "Dividing line", function () { exec("insertHorizontalRule"); }),
      sep(),
      btn("&#8630;", "Undo", function () { exec("undo"); }), btn("&#8631;", "Redo", function () { exec("redo"); }),
      btn("Tx", "Clear formatting", function () { exec("removeFormat"); }),
      btn("&lt;/&gt;", "Edit the HTML", toggleSource, "rt-wide")
    ].forEach(function (el) { bar.appendChild(el); });

    /* Picture options: appear when a picture is clicked. */
    function imgBtn(label, title, fn) { return btn(label, title, function () { if (selected) { fn(selected); sync(); } }); }
    function setPos(img, pos) { ["img-left", "img-right", "img-center", "img-full"].forEach(function (c) { img.classList.remove(c); }); img.classList.add(pos); if (pos === "img-full") img.style.width = ""; else if (!img.style.width) img.style.width = pos === "img-center" ? "60%" : "40%"; }
    function setWidth(img, w) { img.style.width = w; if (img.classList.contains("img-full")) { img.classList.remove("img-full"); img.classList.add("img-center"); } }
    [
      imgBtn("&#9664; Left, text wraps", "Picture on the left, text flows around it", function (i) { setPos(i, "img-left"); }),
      imgBtn("Centre", "Picture in the middle, on its own line", function (i) { setPos(i, "img-center"); }),
      imgBtn("Right, text wraps &#9654;", "Picture on the right, text flows around it", function (i) { setPos(i, "img-right"); }),
      imgBtn("Full width", "Picture across the whole page", function (i) { setPos(i, "img-full"); }),
      sep(),
      imgBtn("S", "Small (25%)", function (i) { setWidth(i, "25%"); }), imgBtn("M", "Medium (40%)", function (i) { setWidth(i, "40%"); }),
      imgBtn("L", "Large (60%)", function (i) { setWidth(i, "60%"); }),
      sep(),
      imgBtn("Description", "Describe the picture (for screen readers and Google)", function (i) { var t = window.prompt("What does the picture show?", i.alt || ""); if (t !== null) i.alt = t; }),
      imgBtn("Remove", "Remove the picture", function (i) { i.remove(); selected = null; imgbar.hidden = true; })
    ].forEach(function (el) { imgbar.appendChild(el); });

    page.addEventListener("click", function (e) {
      page.querySelectorAll("img.rt-selected").forEach(function (i) { i.classList.remove("rt-selected"); });
      if (e.target.tagName === "IMG") { selected = e.target; selected.classList.add("rt-selected"); imgbar.hidden = false; }
      else { selected = null; imgbar.hidden = true; }
    });
    page.addEventListener("input", sync);
    page.addEventListener("blur", sync);
    source.addEventListener("input", sync);
    page.addEventListener("paste", function (e) { // paste as clean text unless it is an image/file
      var files = e.clipboardData && e.clipboardData.files;
      if (files && files.length && /^image\//.test(files[0].type)) { e.preventDefault(); upload(files[0]); return; }
      var html = e.clipboardData && e.clipboardData.getData("text/html");
      if (!html) return;
      e.preventDefault();
      var tmp = document.createElement("div"); tmp.innerHTML = html;
      tmp.querySelectorAll("script,style,meta,link,iframe").forEach(function (n) { n.remove(); });
      tmp.querySelectorAll("*").forEach(function (n) { n.removeAttribute("class"); n.removeAttribute("id"); n.removeAttribute("lang"); if (n.tagName === "IMG") n.remove(); });
      document.execCommand("insertHTML", false, tmp.innerHTML);
    });
    page.addEventListener("drop", function (e) {
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f && /^image\//.test(f.type)) { e.preventDefault(); upload(f); }
    });

    wrap.appendChild(bar); wrap.appendChild(imgbar); wrap.appendChild(page); wrap.appendChild(source); wrap.appendChild(status); wrap.appendChild(file);
    ta.style.display = "none"; ta.parentNode.insertBefore(wrap, ta.nextSibling);
    try { document.execCommand("styleWithCSS", false, true); document.execCommand("defaultParagraphSeparator", false, "p"); } catch (e) {}
    if (form) form.addEventListener("submit", sync);
    sync();
  }

  function init() { document.querySelectorAll("textarea.js-rich").forEach(function (ta) { if (!ta.dataset.rtDone) { ta.dataset.rtDone = "1"; build(ta); } }); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  // Inline forms added with "Add another" in the admin
  document.addEventListener("formset:added", function () { setTimeout(init, 0); });
})();
