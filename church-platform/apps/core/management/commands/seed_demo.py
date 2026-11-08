"""Load a small set of demo data so the site isn't empty on first run.

    python manage.py seed_demo

The history entries are brief, widely accepted summaries meant as placeholders
for layout and testing. Replace them with properly sourced content (and attach
Sources in the admin) before publishing to the public.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.churches.models import Branch, BranchLeader
from apps.leadership.models import Council, CouncilMember
from apps.community.models import Announcement, Event, Ministry
from apps.core.models import PublishStatus
from apps.giving.models import Fund
from apps.history.models import Era, Figure, HistoricalEvent

ERAS = [
    ("Apostolic Age", "apostolic-age", 30, 100, "The first generation of Christians, from Pentecost to the death of the last apostles."),
    ("Early Church", "early-church", 100, 476, "Persecution, legalization, and the great ecumenical councils."),
    ("Medieval Church", "medieval-church", 476, 1517, "Monasticism, the growth of Christendom, and the division of East and West."),
    ("Reformation & After", "reformation", 1517, None, "The Reformation and the many traditions that followed."),
]

EVENTS = [
    ("Pentecost", "pentecost", "apostolic-age", 30, None, "c. AD 30–33",
     "According to the Book of Acts, the Holy Spirit came upon the disciples in Jerusalem, traditionally regarded as the birth of the church."),
    ("Edict of Milan", "edict-of-milan", "early-church", 313, None, "",
     "Emperors Constantine and Licinius agreed to tolerate Christianity throughout the Roman Empire."),
    ("Council of Nicaea", "council-of-nicaea", "early-church", 325, None, "",
     "The first ecumenical council, convened by Constantine, addressed the teaching of Arius and produced the original form of the Nicene Creed."),
    ("Council of Chalcedon", "council-of-chalcedon", "early-church", 451, None, "",
     "The fourth ecumenical council defined Christ as one person in two natures, divine and human."),
    ("East–West Schism", "east-west-schism", "medieval-church", 1054, None, "",
     "Mutual excommunications between representatives of Rome and Constantinople marked a lasting division between the Latin and Greek churches."),
    ("Ninety-Five Theses", "ninety-five-theses", "reformation", 1517, None, "",
     "Martin Luther's theses on indulgences, circulated in 1517, became a catalyst for the Protestant Reformation."),
]

FIGURES = [
    ("Constantine the Great", "constantine", "Roman Emperor", 272, 337),
    ("Martin Luther", "martin-luther", "Reformer and theologian", 1483, 1546),
]


class Command(BaseCommand):
    help = "Create demo eras, events, figures, branches and a fund (idempotent)."

    def handle(self, *args, **options):
        eras = {}
        for name, slug, start, end, summary in ERAS:
            eras[slug], _ = Era.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "start_year": start, "end_year": end, "summary": summary},
            )

        for name, slug, bio_title, born, died in FIGURES:
            Figure.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "title": bio_title, "born_year": born, "died_year": died,
                          "status": PublishStatus.PUBLISHED},
            )

        for title, slug, era_slug, year, year_end, display, summary in EVENTS:
            event, _ = HistoricalEvent.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title, "era": eras[era_slug], "year_start": year, "year_end": year_end,
                    "date_display": display, "summary": summary, "body": summary,
                    "status": PublishStatus.PUBLISHED,
                },
            )
        HistoricalEvent.objects.get(slug="edict-of-milan").figures.add(Figure.objects.get(slug="constantine"))
        HistoricalEvent.objects.get(slug="council-of-nicaea").figures.add(Figure.objects.get(slug="constantine"))
        HistoricalEvent.objects.get(slug="ninety-five-theses").figures.add(Figure.objects.get(slug="martin-luther"))

        # The church's real structure comes from `import_stations`; no sample units are created here.
        from apps.churches.structure import convert_legacy_headquarters, remove_demo_units

        convert_legacy_headquarters(self.stdout.write)
        remove_demo_units(self.stdout.write)
        local = Branch.objects.filter(is_national_headquarters=True).first()
        council, made = Council.objects.get_or_create(
            slug="general-council",
            defaults={"name": "General Council", "order": 1,
                      "description": "The governing body that oversees the whole church. Edit these entries in the admin."},
        )
        if made:
            for i, title in enumerate((
                "General Overseer", "Deputy General Overseer", "General Secretary",
                "Financial Secretary", "General Treasurer", "Public Relations Officer",
            ), start=1):
                CouncilMember.objects.create(council=council, name="Name to be added", title=title, order=i)
        if local:  # sample posts go on the National Headquarters station, if it exists
            Announcement.objects.get_or_create(
                branch=local, title="Welcome",
                defaults={"body": "Welcome to our new branch space. Announcements will appear here.", "is_pinned": True},
            )
            Event.objects.get_or_create(
                branch=local, title="Sunday Service",
                defaults={"description": "Join us for worship.", "starts_at": timezone.now() + timedelta(days=3),
                          "location": "Main sanctuary"},
            )
            for name, slug in (("Choir", "choir"), ("Youth Fellowship", "youth"), ("Women's Fellowship", "women")):
                Ministry.objects.get_or_create(
                    branch=local, slug=slug, defaults={"name": name, "description": f"{name} of {local.name}."}
                )
        Fund.objects.get_or_create(slug="general", defaults={"name": "General Fund", "description": "Supports the work of the church."})
        Fund.objects.get_or_create(
            slug="building", defaults={"name": "Building Fund", "branch": local, "description": "Supports our building projects."}
        )

        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
