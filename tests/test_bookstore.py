from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from apps.bookstore.models import Author, Book, Chapter, DevotionalEntry, Order

pytestmark = pytest.mark.django_db


@pytest.fixture
def book():
    b = Book.objects.create(
        title="Life for You", series="Daily Devotional", is_published=True,
        sells_print=True, print_price=Decimal("20.00"), stock=5,
        sells_ebook=True, ebook_price=Decimal("5.00"),
    )
    b.authors.add(Author.objects.create(name="Pastor A", is_our_minister=True))
    b.ebook_file.save("life.pdf", ContentFile(b"%PDF-1.4 fake"))
    Chapter.objects.create(book=b, number=1, title="Beginnings", body="One.\n\nTwo.", is_preview=True)
    Chapter.objects.create(book=b, number=2, title="Going on", body="Paid chapter.")
    yield b
    b.ebook_file.delete(save=False)


def _checkout(client, **extra):
    data = {"name": "Ada", "email": "ada@example.org", "payment_method": "transfer", "delivery": "pickup"}
    data.update(extra)
    return client.post(reverse("bookstore:checkout"), data)


def test_shop_lists_only_published_books(client, book):
    Book.objects.create(title="Secret Draft", is_published=False)
    html = client.get(reverse("bookstore:list")).content.decode()
    assert "Life for You" in html and "Secret Draft" not in html
    assert client.get(reverse("bookstore:list"), {"q": "pastor a"}).context["count"] == 1
    assert client.get(reverse("bookstore:list"), {"format": "free"}).context["count"] == 0


def test_cart_prices_come_from_the_database(client, book):
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "print", "quantity": 2})
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "ebook", "price": "0.01"})
    assert client.get(reverse("bookstore:cart")).context["subtotal"] == Decimal("45.00")


def test_cannot_add_unavailable_format(client, book):
    book.stock = 0
    book.save()
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "print", "quantity": 1})
    assert client.get(reverse("bookstore:cart")).context["lines"] == []


def test_checkout_makes_a_pending_order_and_empties_the_cart(client, book, settings):
    settings.BOOKSTORE_SHIPPING_FEE = "3"
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "print", "quantity": 2})
    r = _checkout(client, delivery="ship", address="1 Road", city="Aba")
    order = Order.objects.get()
    assert r.status_code == 302 and r["Location"] == order.get_absolute_url()
    assert order.status == "pending" and order.shipping == Decimal("3") and order.total == Decimal("43.00")
    assert client.get(reverse("bookstore:cart")).context["lines"] == []
    assert "BK-" in client.get(order.get_absolute_url()).content.decode()


def test_delivery_needs_an_address(client, book):
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "print", "quantity": 1})
    r = _checkout(client, delivery="ship")
    assert r.status_code == 200 and not Order.objects.exists()


def test_marking_paid_takes_stock_out_once(client, book):
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "print", "quantity": 2})
    _checkout(client)
    order = Order.objects.get()
    assert order.mark_paid() is True and order.mark_paid() is False
    book.refresh_from_db()
    assert book.stock == 3 and order.status == "paid"


def test_ebook_download_only_after_payment(client, book):
    url = reverse("bookstore:download", args=[book.slug])
    assert client.get(url).status_code == 404  # strangers
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "ebook"})
    _checkout(client)
    assert client.get(url).status_code == 404  # ordered but not paid
    Order.objects.get().mark_paid()
    r = client.get(url)
    assert r.status_code == 200 and b"".join(r.streaming_content).startswith(b"%PDF")
    assert client.__class__().get(url).status_code == 404  # another browser still cannot


def test_ebook_file_is_not_under_public_media(book):
    from django.conf import settings
    assert not str(book.ebook_file.path).startswith(str(settings.MEDIA_ROOT))


def test_free_preview_and_locked_chapters(client, book):
    assert client.get(reverse("bookstore:read", args=[book.slug, 1])).status_code == 200
    assert client.get(reverse("bookstore:read", args=[book.slug, 2])).status_code == 302  # locked
    book.free_to_read = True
    book.save()
    assert client.get(reverse("bookstore:read", args=[book.slug, 2])).status_code == 200


def test_buyer_can_read_every_chapter(client, book):
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "ebook"})
    _checkout(client)
    Order.objects.get().mark_paid()
    assert client.get(reverse("bookstore:read", args=[book.slug, 2])).status_code == 200


def test_free_order_is_paid_immediately(client):
    b = Book.objects.create(title="Free Gift", is_published=True, sells_ebook=True, ebook_price=Decimal("0"))
    b.ebook_file.save("g.pdf", ContentFile(b"%PDF"))
    try:
        client.post(reverse("bookstore:cart_add", args=[b.slug]), {"format": "ebook"})
        _checkout(client)
        assert Order.objects.get().status == "paid"
    finally:
        b.ebook_file.delete(save=False)


def test_test_mode_online_payment(client, book, settings):
    settings.DEBUG, settings.PAYMENT_PROVIDER = True, "dummy"
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "ebook"})
    r = _checkout(client, payment_method="online")
    order = Order.objects.get()
    assert r["Location"] == reverse("bookstore:dev_pay", args=[order.reference])
    client.post(r["Location"])
    order.refresh_from_db()
    assert order.status == "paid"


def test_dev_pay_is_closed_in_production(client, book, settings):
    settings.DEBUG = False
    client.post(reverse("bookstore:cart_add", args=[book.slug]), {"format": "ebook"})
    _checkout(client)
    assert client.get(reverse("bookstore:dev_pay", args=[Order.objects.get().reference])).status_code == 404


def test_daily_devotional_today_and_no_future_peeking(client):
    today = timezone.localdate()
    DevotionalEntry.objects.create(date=today, title="Morning light", body="Be still.", scripture="Ps 46:10")
    future = today + timezone.timedelta(days=3)
    DevotionalEntry.objects.create(date=future, title="Future word", body="x")
    assert "Morning light" in client.get(reverse("bookstore:devotional")).content.decode()
    assert client.get(reverse("bookstore:devotional_day", args=[future.isoformat()])).status_code == 404
    assert "Morning light" in client.get(reverse("core:home")).content.decode()


def test_admin_pages_for_the_shop_work(admin_client, book):
    for name in ("book", "order", "author", "category", "devotionalentry"):
        assert admin_client.get(reverse(f"admin:bookstore_{name}_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:bookstore_book_add")).status_code == 200
    assert admin_client.get(reverse("admin:bookstore_book_change", args=[book.pk])).status_code == 200
