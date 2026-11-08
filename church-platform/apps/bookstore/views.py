import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings

from . import services as svc
from .forms import CheckoutForm
from .models import Author, Book, Category, Chapter, DevotionalEntry, Order

PAGE_SIZE = 12
SORTS = {"new": "-created_at", "title": "title", "price": "price_sort"}


def _published():
    return Book.objects.filter(is_published=True).select_related("category").prefetch_related("authors")


def book_list(request):
    g = request.GET
    q, cat, source, fmt, sort = g.get("q", "").strip(), g.get("category", ""), g.get("source", ""), g.get("format", ""), g.get("sort", "")
    qs = _published()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(subtitle__icontains=q) | Q(authors__name__icontains=q)
                       | Q(series__icontains=q) | Q(description__icontains=q)).distinct()
    if cat:
        qs = qs.filter(category__slug=cat)
    if source in dict(Book.Source.choices):
        qs = qs.filter(source=source)
    if fmt == "print":
        qs = qs.filter(sells_print=True, stock__gt=0)
    elif fmt == "ebook":
        qs = qs.filter(sells_ebook=True)
    elif fmt == "free":
        qs = qs.filter(free_to_read=True)
    books = list(qs)
    if sort == "title":
        books.sort(key=lambda b: b.title.lower())
    elif sort == "price":
        books.sort(key=lambda b: (b.price_from is None, b.price_from or 0))
    page = Paginator(books, PAGE_SIZE).get_page(g.get("page"))
    keep = "&".join(f"{k}={v}" for k, v in g.items() if k != "page" and v)
    return render(request, "books/list.html", {
        "page": page, "q": q, "category": cat, "source": source, "format": fmt, "sort": sort,
        "categories": Category.objects.all(), "sources": Book.Source.choices,
        "count": len(books), "base_qs": keep, "featured": _published().filter(is_featured=True)[:4] if not (q or cat or source or fmt) else [],
        "today": _today_entry(),
    })


def book_detail(request, slug):
    book = get_object_or_404(_published(), slug=slug)
    chapters = list(book.chapters.all())
    owned = svc.owns_ebook(request, book)
    for c in chapters:
        c.open = book.free_to_read or c.is_preview or owned
    related = _published().filter(Q(category=book.category) | Q(authors__in=book.authors.all())).exclude(pk=book.pk).distinct()[:4]
    return render(request, "books/detail.html", {
        "book": book, "chapters": chapters, "owned": owned, "related": related,
        "tag": book.get_source_display(),
    })


def read(request, slug, number):
    book = get_object_or_404(_published(), slug=slug)
    chapters = list(book.chapters.all())
    chapter = next((c for c in chapters if c.number == number), None)
    if chapter is None:
        raise Http404
    if not svc.can_read_chapter(request, book, chapter):
        messages.info(request, "This chapter is for readers of the e-book. Buy it to read on, or read a free preview chapter.")
        return redirect(book)
    idx = chapters.index(chapter)
    nxt = chapters[idx + 1] if idx + 1 < len(chapters) else None
    prev = chapters[idx - 1] if idx else None
    return render(request, "books/read.html", {
        "book": book, "chapter": chapter, "chapters": chapters, "next": nxt, "prev": prev,
        "paragraphs": [p.strip() for p in chapter.body.split("\n\n") if p.strip()],
        "can_next": bool(nxt and svc.can_read_chapter(request, book, nxt)),
    })


# ---- daily devotional -------------------------------------------------------
def _today_entry():
    today = timezone.localdate()
    qs = DevotionalEntry.objects.filter(is_published=True).select_related("book")
    return qs.filter(date=today).first() or qs.filter(date__lte=today).first()


def _devotional_page(request, entry):
    base = DevotionalEntry.objects.filter(is_published=True)
    return render(request, "books/devotional.html", {
        "entry": entry,
        "paragraphs": [p.strip() for p in entry.body.split("\n\n") if p.strip()] if entry else [],
        "prev": base.filter(date__lt=entry.date).order_by("-date").first() if entry else None,
        "next": base.filter(date__gt=entry.date, date__lte=timezone.localdate()).order_by("date").first() if entry else None,
    })


def devotional_today(request):
    return _devotional_page(request, _today_entry())


def devotional_day(request, day):
    try:
        d = datetime.date.fromisoformat(day)
    except ValueError:
        raise Http404
    entry = DevotionalEntry.objects.filter(is_published=True, date=d).first()
    if entry is None or d > timezone.localdate():
        raise Http404
    return _devotional_page(request, entry)


def devotional_archive(request):
    qs = DevotionalEntry.objects.filter(is_published=True, date__lte=timezone.localdate())
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "books/devotional_archive.html", {"page": page, "base_qs": ""})


# ---- cart & checkout --------------------------------------------------------
def cart(request):
    lines, subtotal = svc.cart_lines(request)
    return render(request, "books/cart.html", {"lines": lines, "subtotal": subtotal, "currency": settings.DEFAULT_CURRENCY,
                                              "blocked": any(l["problem"] for l in lines)})


@require_POST
def cart_add(request, slug):
    book = get_object_or_404(_published(), slug=slug)
    try:
        qty = int(request.POST.get("quantity", 1))
    except ValueError:
        qty = 1
    problem = svc.add_to_cart(request, book, request.POST.get("format", ""), qty)
    if problem:
        messages.error(request, problem)
        return redirect(book)
    messages.success(request, f"“{book.title}” was added to your cart.")
    return redirect("bookstore:cart")


@require_POST
def cart_update(request):
    key = request.POST.get("key", "")
    if request.POST.get("remove"):
        svc.set_quantity(request, key, 0)
    else:
        try:
            svc.set_quantity(request, key, int(request.POST.get("quantity", 1)))
        except ValueError:
            pass
    return redirect("bookstore:cart")


def checkout(request):
    lines, _ = svc.cart_lines(request)
    good = [l for l in lines if not l["problem"]]
    if not good or len(good) != len(lines):
        if lines:
            messages.error(request, "Please fix the items marked in your cart first.")
        return redirect("bookstore:cart")
    has_print = any(l["fmt"] == "print" for l in good)
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name(), "email": request.user.email, "phone": getattr(request.user, "phone", "")}
    form = CheckoutForm(request.POST or None, has_print=has_print, initial=initial)
    delivery = request.POST.get("delivery", "ship") if has_print else Order.Delivery.DIGITAL
    subtotal, fee, total = svc.totals(lines, delivery)
    if request.method == "POST" and form.is_valid():
        try:
            order = svc.create_order(request, form.cleaned_data, lines)
        except ValueError:
            return redirect("bookstore:cart")
        svc.clear_cart(request)
        svc.send_confirmation(request, order)
        if order.status == Order.Status.PENDING and order.payment_method == Order.Payment.ONLINE:
            return redirect("bookstore:dev_pay", reference=order.reference)
        return redirect(order)
    return render(request, "books/checkout.html", {
        "form": form, "lines": lines, "subtotal": subtotal, "shipping": fee, "total": total,
        "currency": settings.DEFAULT_CURRENCY, "has_print": has_print, "fee": svc.shipping_fee(),
    })


def order_detail(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("items__book"), reference=reference)
    svc.remember_order(request, order)  # whoever holds the private link can see it
    return render(request, "books/order.html", {
        "order": order, "payment_instructions": SiteSettings.load().payment_instructions,
        "ebooks": [i for i in order.items.all() if i.fmt == "ebook"] if order.is_paid else [],
    })


def dev_pay(request, reference):
    """Stand-in payment page for development (PAYMENT_PROVIDER=dummy and DEBUG on)."""
    if not svc.online_payments_available():
        raise Http404
    order = get_object_or_404(Order, reference=reference)
    if request.method == "POST":
        order.mark_paid()
        svc.send_confirmation(request, order)
        return redirect(order)
    return render(request, "books/dev_pay.html", {"order": order})


@login_required
def library(request):
    orders = request.user.book_orders.prefetch_related("items__book")
    owned = {}
    for o in orders:
        if o.is_paid:
            for i in o.items.all():
                if i.fmt == "ebook":
                    owned[i.book_id] = i.book
    return render(request, "books/library.html", {"orders": orders, "owned": list(owned.values())})


def download(request, slug):
    book = get_object_or_404(Book, slug=slug, is_published=True)
    if not (book.ebook_file and svc.owns_ebook(request, book)):
        raise Http404
    try:
        f = book.ebook_file.open("rb")
    except FileNotFoundError:
        raise Http404
    name = f"{book.slug}.pdf"
    resp = FileResponse(f, as_attachment=True, filename=name, content_type="application/pdf")
    resp["Cache-Control"] = "private, no-store"
    return resp
