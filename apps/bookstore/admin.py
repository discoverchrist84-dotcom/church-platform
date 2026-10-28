from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_base import FriendlyAdmin, flag_action, picture_preview

from .models import Author, Book, Category, Chapter, DevotionalEntry, Order, OrderItem


class ChapterInline(admin.StackedInline):
    model = Chapter
    extra = 0
    classes = ("collapse",)
    verbose_name_plural = "Chapters (for reading online). Tick 'free preview' on the ones anyone may read."
    fields = (("number", "title", "is_preview"), "body")


@admin.register(Book)
class BookAdmin(FriendlyAdmin):
    help_list = "Every book in the shop and library: your ministers' books and books from other churches. Untick 'published' to hide one without deleting it."
    help_form = ("Fill in the book's details, then set how it is sold. A printed copy needs a price and copies in stock. "
                 "An e-book needs a price and the PDF file. Add chapters at the bottom so people can read online, "
                 "and tick 'free to read' to open the whole book to everyone.")
    list_display = ("thumb", "title", "series", "source", "print_price", "stock", "ebook_price", "free_to_read", "is_featured", "is_published")
    list_display_links = ("thumb", "title")
    list_editable = ("is_featured", "is_published")
    list_filter = ("is_published", "source", "category", "sells_print", "sells_ebook", "free_to_read")
    search_fields = ("title", "subtitle", "authors__name", "series", "isbn")
    autocomplete_fields = ("authors", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("cover_preview",)
    inlines = [ChapterInline]
    actions = [
        flag_action("is_published", True, "Show selected on the website", "%(n)d book shown.", "%(n)d books shown."),
        flag_action("is_published", False, "Hide selected from the website", "%(n)d book hidden.", "%(n)d books hidden."),
        flag_action("is_featured", True, "Feature selected on the home page", "%(n)d book featured.", "%(n)d books featured."),
    ]
    fieldsets = (
        ("The book", {"fields": ("title", "slug", "subtitle", "series", "authors", "category", "source", "publisher", "description")}),
        ("Cover", {"fields": (("cover", "cover_preview"),)}),
        ("Details", {"classes": ("collapse",), "fields": ("language", "pages", "year", "isbn")}),
        ("Printed copies", {"description": "Sold and delivered by the church.", "fields": ("sells_print", "print_price", "stock")}),
        ("E-book (PDF download)", {"description": "Buyers download it instantly after payment. The file is private.", "fields": ("sells_ebook", "ebook_price", "ebook_file")}),
        ("Reading online", {"fields": ("free_to_read",)}),
        ("Showing on the website", {"fields": ("is_published", "is_featured")}),
    )

    @admin.display(description="")
    def thumb(self, obj):
        url = obj.cover.url if obj.cover and obj.cover.storage.exists(obj.cover.name) else ""
        return format_html('<img src="{}" class="athumb">', url) if url else "📖"

    @admin.display(description="Saved cover")
    def cover_preview(self, obj):
        return picture_preview(obj, "cover")


@admin.register(Author)
class AuthorAdmin(FriendlyAdmin):
    help_list = "Writers: your own ministers, and authors from other churches and denominations."
    help_form = "Add the author's name and, if they belong to another church, which one."
    list_display = ("name", "affiliation", "is_our_minister")
    list_filter = ("is_our_minister",)
    search_fields = ("name", "affiliation")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(FriendlyAdmin):
    help_list = "Topics that group the books, e.g. Devotionals, Prayer, Doctrine, Family."
    help_form = "Give the category a name. Smaller 'order' numbers show first."
    list_display = ("name", "order")
    list_editable = ("order",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DevotionalEntry)
class DevotionalEntryAdmin(FriendlyAdmin):
    help_list = "One reading per day for a daily devotional such as 'Life for You'. Readings show on their date and stay in the archive."
    help_form = "Pick the date, write the title, scripture, reading and an optional prayer. Leave a blank line between paragraphs."
    list_display = ("date", "title", "scripture", "book", "is_published")
    list_editable = ("is_published",)
    list_filter = ("is_published", "book")
    search_fields = ("title", "scripture", "body")
    date_hierarchy = "date"
    autocomplete_fields = ("book",)


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("book", "fmt", "quantity", "unit_price")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(FriendlyAdmin):
    help_list = ("Book orders. For bank transfers, open the order or tick several and use the action 'Mark as paid' when the money arrives: "
                 "e-books then open for the buyer and printed copies come out of stock. Then use 'Mark as sent'.")
    help_form = "Change the status as the order moves along. Customer details and items are locked, as they are a record of what was bought."
    list_display = ("number_display", "name", "email", "total", "currency", "payment_method", "delivery", "status", "created_at")
    list_filter = ("status", "payment_method", "delivery")
    search_fields = ("name", "email", "phone")
    date_hierarchy = "created_at"
    inlines = [ItemInline]
    readonly_fields = ("reference", "user", "subtotal", "shipping", "total", "currency", "paid_at", "provider_reference", "created_at")
    fieldsets = (
        ("Order", {"fields": ("reference", "status", "payment_method", "paid_at", "created_at")}),
        ("Customer", {"fields": ("user", "name", "email", "phone")}),
        ("Delivery", {"fields": ("delivery", "address", "city", "state", "country", "note")}),
        ("Money", {"fields": ("subtotal", "shipping", "total", "currency", "provider_reference")}),
    )
    actions = ["mark_paid", "mark_sent", "mark_completed", "mark_cancelled"]

    @admin.display(description="Order", ordering="id")
    def number_display(self, obj):
        return obj.number

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark as paid (opens e-books, takes printed copies out of stock)")
    def mark_paid(self, request, queryset):
        n = sum(1 for o in queryset.filter(status=Order.Status.PENDING) if o.mark_paid())
        self.message_user(request, f"{n} order(s) marked as paid.")

    @admin.action(description="Mark as sent out")
    def mark_sent(self, request, queryset):
        n = queryset.filter(status=Order.Status.PAID).update(status=Order.Status.SHIPPED)
        self.message_user(request, f"{n} order(s) marked as sent.")

    @admin.action(description="Mark as completed")
    def mark_completed(self, request, queryset):
        n = queryset.filter(status__in=[Order.Status.PAID, Order.Status.SHIPPED]).update(status=Order.Status.COMPLETED)
        self.message_user(request, f"{n} order(s) completed.")

    @admin.action(description="Cancel (only orders still waiting for payment)")
    def mark_cancelled(self, request, queryset):
        n = queryset.filter(status=Order.Status.PENDING).update(status=Order.Status.CANCELLED)
        self.message_user(request, f"{n} order(s) cancelled.")
