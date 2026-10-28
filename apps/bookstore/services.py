"""Cart, orders and who may read or download what. Kept apart from the views so it is easy to test."""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Book, Order, OrderItem

log = logging.getLogger(__name__)
SESSION_CART = "book_cart"
SESSION_ORDERS = "book_orders"
MAX_QTY = 20


# ---- payment options -------------------------------------------------------
def online_payments_available():
    """Online card payment only exists in test mode for now (see apps/giving/providers.py for adding a real gateway)."""
    return bool(settings.DEBUG and settings.PAYMENT_PROVIDER == "dummy")


def shipping_fee():
    return Decimal(str(getattr(settings, "BOOKSTORE_SHIPPING_FEE", "0")))


# ---- the cart (kept in the visitor's session) --------------------------------
def _cart(request):
    return request.session.setdefault(SESSION_CART, {})


def add_to_cart(request, book, fmt, qty=1):
    if fmt not in ("print", "ebook"):
        return "Choose a format."
    if fmt == "print" and not book.can_buy_print:
        return "Printed copies of this book are not available right now."
    if fmt == "ebook" and not book.can_buy_ebook:
        return "The e-book is not available for sale."
    cart, key = _cart(request), f"{book.pk}:{fmt}"
    qty = 1 if fmt == "ebook" else max(1, min(qty, MAX_QTY))
    cart[key] = 1 if fmt == "ebook" else min(cart.get(key, 0) + qty, MAX_QTY)
    request.session.modified = True
    return ""


def set_quantity(request, key, qty):
    cart = _cart(request)
    if key in cart:
        if qty <= 0:
            del cart[key]
        else:
            cart[key] = 1 if key.endswith(":ebook") else min(qty, MAX_QTY)
        request.session.modified = True


def clear_cart(request):
    request.session.pop(SESSION_CART, None)


def cart_count(request):
    cart = request.session.get(SESSION_CART) or {}
    return sum(cart.values()) if cart else 0


def cart_lines(request):
    """[{key, book, fmt, qty, unit, total, problem}], subtotal. Prices always come from the database, never the browser."""
    cart = request.session.get(SESSION_CART) or {}
    ids = {int(k.split(":")[0]) for k in cart if k.split(":")[0].isdigit()}
    books = {b.pk: b for b in Book.objects.filter(pk__in=ids, is_published=True).prefetch_related("authors")}
    lines, subtotal = [], Decimal("0")
    for key, qty in cart.items():
        pk, _, fmt = key.partition(":")
        book = books.get(int(pk)) if pk.isdigit() else None
        if not book or fmt not in ("print", "ebook"):
            continue
        unit = book.unit_price(fmt)
        problem = ""
        if fmt == "print" and not book.can_buy_print:
            problem = "No longer available."
        elif fmt == "print" and qty > book.stock:
            problem = f"Only {book.stock} in stock."
        elif fmt == "ebook" and not book.can_buy_ebook:
            problem = "No longer available."
        if unit is None:
            problem = problem or "No price set."
            unit = Decimal("0")
        total = unit * qty
        if not problem:
            subtotal += total
        lines.append({"key": key, "book": book, "fmt": fmt, "qty": qty, "unit": unit, "total": total, "problem": problem})
    return lines, subtotal


def totals(lines, delivery):
    ok = [l for l in lines if not l["problem"]]
    subtotal = sum((l["total"] for l in ok), Decimal("0"))
    ships = delivery == Order.Delivery.SHIP and any(l["fmt"] == "print" for l in ok)
    fee = shipping_fee() if ships else Decimal("0")
    return subtotal, fee, subtotal + fee


# ---- orders -----------------------------------------------------------------
@transaction.atomic
def create_order(request, data, lines):
    ok = [l for l in lines if not l["problem"]]
    if not ok:
        raise ValueError("Nothing to order.")
    has_print = any(l["fmt"] == "print" for l in ok)
    delivery = data["delivery"] if has_print else Order.Delivery.DIGITAL
    subtotal, fee, total = totals(ok, delivery)
    user = request.user if request.user.is_authenticated else None
    order = Order.objects.create(
        user=user, name=data["name"], email=data["email"], phone=data.get("phone", ""),
        delivery=delivery, address=data.get("address", ""), city=data.get("city", ""),
        state=data.get("state", ""), country=data.get("country", ""), note=data.get("note", ""),
        payment_method=data["payment_method"], subtotal=subtotal, shipping=fee, total=total,
        currency=settings.DEFAULT_CURRENCY,
    )
    OrderItem.objects.bulk_create([
        OrderItem(order=order, book=l["book"], fmt=l["fmt"], quantity=l["qty"], unit_price=l["unit"]) for l in ok
    ])
    if total == 0:  # everything on the order is free: nothing to pay
        order.mark_paid()
    remember_order(request, order)
    return order


def remember_order(request, order):
    """Lets the buyer open their e-books in this browser even without an account."""
    refs = request.session.setdefault(SESSION_ORDERS, [])
    if str(order.reference) not in refs:
        refs.append(str(order.reference))
        request.session.modified = True


def send_confirmation(request, order):
    try:
        lines = "\n".join(f"- {i}" for i in order.items.all())
        send_mail(
            subject=f"Your order {order.number}",
            message=(f"Thank you, {order.name}.\n\n{lines}\n\nTotal: {order.total} {order.currency}\n"
                     f"Status: {order.get_status_display()}\n\nYour order page (downloads and updates):\n"
                     f"{request.build_absolute_uri(order.get_absolute_url())}\n"),
            from_email=None, recipient_list=[order.email], fail_silently=True,
        )
    except Exception:  # noqa: BLE001  never let email trouble break an order
        log.exception("Could not send order email for %s", order.pk)


# ---- who may read / download --------------------------------------------------
def owns_ebook(request, book):
    """True for staff, and for anyone with a paid order that includes this book's e-book."""
    user = request.user
    if user.is_authenticated and (user.is_staff or user.is_superuser):
        return True
    paid = (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.COMPLETED)
    q = OrderItem.objects.filter(book=book, fmt="ebook", order__status__in=paid)
    if user.is_authenticated and q.filter(order__user=user).exists():
        return True
    refs = request.session.get(SESSION_ORDERS) or []
    return bool(refs) and q.filter(order__reference__in=refs).exists()


def can_read_chapter(request, book, chapter):
    return book.free_to_read or chapter.is_preview or owns_ebook(request, book)
