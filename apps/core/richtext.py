"""Rich text: a strict allow-list sanitizer, so formatted stories can be shown safely.

Editors write formatted text in the admin (bold, italics, headings, lists, pictures that text wraps
around...). The HTML is cleaned when it is saved AND again when it is shown, so nothing unexpected
(scripts, event handlers, outside frames) can ever get through. Old plain-text stories (blank line =
new paragraph) are still shown correctly.
"""
import re
from html import escape
from html.parser import HTMLParser

from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "strike", "del", "sub", "sup", "span",
    "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "a", "img", "hr", "figure", "figcaption",
}
VOID = {"br", "hr", "img"}
RENAME = {"b": "strong", "i": "em", "strike": "s", "del": "s", "div": "p", "h1": "h2", "h5": "h4", "h6": "h4", "font": "span"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "noscript", "template", "svg", "math", "form", "textarea", "select"}
IMG_CLASSES = {"img-left", "img-right", "img-center", "img-full"}
SAFE_LINK = re.compile(r"^(https?://|mailto:|tel:|/|#)", re.I)
SAFE_SRC = re.compile(r"^(https?://|/)(?!/)", re.I)
HEX = r"#[0-9a-fA-F]{3,8}"
COLOR = re.compile(rf"^({HEX}|rgb\(\s*\d{{1,3}}\s*,\s*\d{{1,3}}\s*,\s*\d{{1,3}}\s*\)|[a-zA-Z]{{3,20}})$")
STYLE_RULES = {
    "color": COLOR,
    "background-color": COLOR,
    "text-align": re.compile(r"^(left|right|center|justify)$"),
    "font-size": re.compile(r"^(small|x-small|medium|large|x-large|xx-large|\d{1,3}(\.\d+)?(px|em|rem|%))$"),
    "font-weight": re.compile(r"^(bold|normal|[1-9]00)$"),
    "font-style": re.compile(r"^(italic|normal)$"),
    "text-decoration": re.compile(r"^(underline|line-through|none)$"),
    "width": re.compile(r"^\d{1,3}(\.\d+)?(%|px)$"),
}
FONT_SIZE = {"1": "x-small", "2": "small", "3": "medium", "4": "large", "5": "x-large", "6": "xx-large", "7": "xx-large"}


def _clean_style(value, tag):
    out = []
    for decl in (value or "").split(";"):
        if ":" not in decl:
            continue
        prop, val = (x.strip().lower() if i == 0 else x.strip() for i, x in enumerate(decl.split(":", 1)))
        rule = STYLE_RULES.get(prop)
        if not rule or not rule.match(val) or (prop == "width" and tag != "img"):
            continue
        out.append(f"{prop}: {val}")
    return "; ".join(out)


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0  # depth inside a dropped element
        self.open = []

    def handle_starttag(self, tag, attrs):
        if self.skip or tag in DROP_WITH_CONTENT:
            if tag in DROP_WITH_CONTENT and tag not in VOID:
                self.skip += 1
            return
        attrs = {k: (v or "") for k, v in attrs}
        extra_style = ""
        if tag == "font":  # execCommand fallbacks
            if attrs.get("color"):
                extra_style += f"color: {attrs['color']};"
            if attrs.get("size") in FONT_SIZE:
                extra_style += f"font-size: {FONT_SIZE[attrs['size']]};"
        tag = RENAME.get(tag, tag)
        if tag not in ALLOWED_TAGS:
            return  # unknown tag: dropped, its text is kept
        keep = []
        if tag == "a":
            href = attrs.get("href", "").strip()
            if not SAFE_LINK.match(href):
                return
            keep.append(f'href="{escape(href, quote=True)}"')
            if href.lower().startswith(("http://", "https://")):
                keep.append('target="_blank" rel="noopener nofollow"')
        elif tag == "img":
            src = attrs.get("src", "").strip()
            if not SAFE_SRC.match(src):
                return
            keep.append(f'src="{escape(src, quote=True)}"')
            keep.append(f'alt="{escape(attrs.get("alt", "")[:300], quote=True)}"')
            keep.append('loading="lazy"')
            cls = " ".join(c for c in attrs.get("class", "").split() if c in IMG_CLASSES)
            if cls:
                keep.append(f'class="{cls}"')
        elif tag == "figure":
            cls = " ".join(c for c in attrs.get("class", "").split() if c in IMG_CLASSES)
            if cls:
                keep.append(f'class="{cls}"')
        style = _clean_style(attrs.get("style", "") + ";" + extra_style, tag)
        if style and tag not in ("br", "hr"):
            keep.append(f'style="{escape(style, quote=True)}"')
        if tag == "span" and not keep:
            return  # an empty wrapper adds nothing
        self.out.append(f"<{tag}{(' ' + ' '.join(keep)) if keep else ''}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_endtag(self, tag):
        if self.skip:
            if tag in DROP_WITH_CONTENT:
                self.skip -= 1
            return
        tag = RENAME.get(tag, tag)
        if tag in self.open:
            while self.open:
                t = self.open.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))

    def result(self):
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out)


_HAS_MARKUP = re.compile(r"<\s*(p|br|strong|b|em|i|u|s|strike|del|sub|sup|font|h[1-6]|ul|ol|li|blockquote|a|img|div|span|figure|hr)\b", re.I)


def clean_html(value):
    """Allow-listed HTML. Plain text is turned into paragraphs. Returns a str (not yet marked safe)."""
    value = (value or "").strip()
    if not value:
        return ""
    if not _HAS_MARKUP.search(value):
        paras = [p.strip() for p in re.split(r"\n\s*\n", value.replace("\r\n", "\n")) if p.strip()]
        return "".join(f"<p>{escape(p, quote=False).replace(chr(10), '<br>')}</p>" for p in paras)
    c = _Cleaner()
    c.feed(value)
    c.close()
    html = c.result()
    html = re.sub(r"<p>(\s|&nbsp;|<br>)*</p>", "", html)  # editors leave empty paragraphs behind
    return html


def render_rich(value):
    return mark_safe(f'<div class="rich">{clean_html(value)}</div>') if (value or "").strip() else ""


def plain_text(value, limit=None):
    """Words only, for summaries, descriptions and notifications."""
    text = strip_tags(clean_html(value).replace("</p>", " ").replace("<br>", " ").replace("</li>", " "))
    text = " ".join(text.replace("&nbsp;", " ").split())
    from html import unescape

    text = unescape(text)
    if limit and len(text) > limit:
        return text[:limit].rsplit(" ", 1)[0] + "…"
    return text
