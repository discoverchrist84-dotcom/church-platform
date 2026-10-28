import uuid
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image


def private_storage():
    """Paid e-book files live outside the public /media/ folder, so they can only be fetched through a checked download link."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def _unique_slug(model, text, pk, fallback):
    base = slugify(text) or fallback
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=pk).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


class Author(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    affiliation = models.CharField(
        max_length=160, blank=True, help_text="e.g. Christ Ascension Church, or the other church or denomination they serve.",
    )
    is_our_minister = models.BooleanField("one of our ministers", default=False)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="authors/", blank=True, validators=[validate_image])

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Author, self.name, self.pk, "author")
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Smaller numbers show first.")

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk, "category")
        super().save(*args, **kwargs)


class Book(TimeStampedModel):
    class Source(models.TextChoices):
        OURS = "ours", "From our ministers"
        OTHER = "other", "From another church or denomination"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=200, blank=True)
    authors = models.ManyToManyField(Author, related_name="books", blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="books")
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.OURS)
    publisher = models.CharField(max_length=160, blank=True, help_text="Publisher or the church/denomination it comes from.")
    series = models.CharField(max_length=120, blank=True, help_text="e.g. Daily Devotional")
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="books/covers/", blank=True, validators=[validate_image],
                              help_text="Front cover. Portrait pictures look best.")
    language = models.CharField(max_length=40, default="English")
    pages = models.PositiveIntegerField(null=True, blank=True)
    isbn = models.CharField("ISBN", max_length=20, blank=True)
    year = models.PositiveSmallIntegerField("year published", null=True, blank=True)

    # printed copies
    sells_print = models.BooleanField("sell printed copies", default=False)
    print_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField("copies in stock", default=0)

    # e-book
    sells_ebook = models.BooleanField("sell the e-book (PDF)", default=False)
    ebook_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ebook_file = models.FileField(
        upload_to="ebooks/", storage=private_storage, blank=True,
        help_text="The PDF buyers can download. It is kept private: only people who paid can get it.",
    )

    # reading online
    free_to_read = models.BooleanField(
        "free to read online for everyone", default=False,
        help_text="Tick to let anyone read every chapter on the website. Otherwise only chapters marked 'free preview' are open.",
    )
    is_featured = models.BooleanField("feature on the home page", default=False)
    is_published = models.BooleanField(default=False, help_text="Untick to hide the book from the website without deleting it.")

    class Meta:
        ordering = ["-is_featured", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Book, self.title, self.pk, "book")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("bookstore:detail", args=[self.slug])

    @property
    def author_names(self):
        return ", ".join(a.name for a in self.authors.all())

    @property
    def can_buy_print(self):
        return bool(self.sells_print and self.print_price is not None and self.stock > 0)

    @property
    def can_buy_ebook(self):
        return bool(self.sells_ebook and self.ebook_price is not None and self.ebook_file)

    @property
    def price_from(self):
        prices = [p for p, ok in ((self.print_price, self.sells_print), (self.ebook_price, self.sells_ebook)) if ok and p is not None]
        return min(prices) if prices else None

    def unit_price(self, fmt):
        return self.print_price if fmt == "print" else self.ebook_price


class Chapter(TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="The text. Leave a blank line between paragraphs.")
    is_preview = models.BooleanField("free preview", default=False, help_text="Anyone can read this chapter, even without buying.")

    class Meta:
        ordering = ["book", "number"]
        constraints = [models.UniqueConstraint(fields=["book", "number"], name="unique_chapter_number")]

    def __str__(self):
        return f"{self.book.title}: {self.number}. {self.title}"

    def get_absolute_url(self):
        return reverse("bookstore:read", args=[self.book.slug, self.number])


class DevotionalEntry(TimeStampedModel):
    """One day of a daily devotional such as "Life for You"."""

    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL, related_name="devotionals",
                             help_text="The devotional book this day belongs to (optional).")
    date = models.DateField(help_text="The day this reading is for.")
    title = models.CharField(max_length=200)
    scripture = models.CharField(max_length=200, blank=True, help_text="e.g. John 3:16")
    body = models.TextField(help_text="The reading. Leave a blank line between paragraphs.")
    prayer = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "devotional reading"
        constraints = [models.UniqueConstraint(fields=["book", "date"], name="one_devotional_per_book_per_day")]

    def __str__(self):
        return f"{self.date}: {self.title}"

    def get_absolute_url(self):
        return reverse("bookstore:devotional_day", args=[self.date.isoformat()])


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for payment"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Sent out"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class Delivery(models.TextChoices):
        SHIP = "ship", "Delivery to my address"
        PICKUP = "pickup", "I will collect it"
        DIGITAL = "digital", "Digital only (no delivery)"

    class Payment(models.TextChoices):
        ONLINE = "online", "Pay online"
        TRANSFER = "transfer", "Bank transfer"
        CASH = "cash", "Pay on delivery / collection"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="book_orders")
    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    delivery = models.CharField(max_length=10, choices=Delivery.choices, default=Delivery.DIGITAL)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField("state / region", max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    payment_method = models.CharField(max_length=10, choices=Payment.choices, default=Payment.TRANSFER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="USD")
    paid_at = models.DateTimeField(null=True, blank=True)
    provider_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.number} ({self.get_status_display()})"

    @property
    def number(self):
        return f"BK-{self.pk or 0:05d}"

    @property
    def is_paid(self):
        return self.status in (self.Status.PAID, self.Status.SHIPPED, self.Status.COMPLETED)

    @property
    def has_print(self):
        return any(i.fmt == "print" for i in self.items.all())

    def get_absolute_url(self):
        return reverse("bookstore:order", args=[self.reference])

    def mark_paid(self, note=""):
        """Idempotent: confirm payment, take printed copies out of stock, and open the e-books."""
        from django.db import transaction

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.status != self.Status.PENDING:
                self.status = order.status
                return False
            order.status = self.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
            for item in order.items.select_related("book"):
                if item.fmt == "print":
                    Book.objects.filter(pk=item.book_id).update(stock=models.F("stock") - item.quantity)
                    Book.objects.filter(pk=item.book_id, stock__lt=0).update(stock=0)
        self.status, self.paid_at = order.status, order.paid_at
        return True


class OrderItem(models.Model):
    class Format(models.TextChoices):
        PRINT = "print", "Printed copy"
        EBOOK = "ebook", "E-book (PDF)"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="order_items")
    fmt = models.CharField("format", max_length=5, choices=Format.choices)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.book.title} ({self.get_fmt_display()})"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
