from django.core.management.base import BaseCommand

from apps.bookstore.models import Author, Book, Category


class Command(BaseCommand):
    help = "Create the church's first two book entries as DRAFTS to fill in (safe to run again)."

    def handle(self, *args, **opts):
        devo, _ = Category.objects.get_or_create(name="Devotionals", defaults={"order": 1})
        teach, _ = Category.objects.get_or_create(name="Teaching", defaults={"order": 2})
        for c, o in (("Prayer", 3), ("Family", 4), ("Doctrine", 5)):
            Category.objects.get_or_create(name=c, defaults={"order": o})
        ours, _ = Author.objects.get_or_create(name="Our ministers", defaults={"is_our_minister": True,
                                                                              "affiliation": "Christ Ascension Church"})
        for title, series, cat in (("Manuels (Ascension Power)", "", teach), ("Life for You", "Daily Devotional", devo)):
            book, made = Book.objects.get_or_create(title=title, defaults={
                "series": series, "category": cat, "source": Book.Source.OURS, "is_published": False,
                "description": "Add the description, cover, price and e-book file in the admin, then tick 'published'.",
            })
            if made:
                book.authors.add(ours)
                self.stdout.write(f"Created draft: {title}")
        self.stdout.write(self.style.SUCCESS("Done. Open Books & shop in the admin to add prices, covers and the e-book files."))
