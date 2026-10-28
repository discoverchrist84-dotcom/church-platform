"""The church's admin site: a guided dashboard instead of Django's flat list of tables."""
from django.contrib import admin
from django.db.models import Exists, OuterRef
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

# (slug, section title, what it is for, icon, [(app_label, ModelName, one-line help), ...])
SECTIONS = [
    ("structure", "Church structure", "Areas, districts, stations (the National Headquarters is one of them) and who leads them.", "🏛️", [
        ("churches", "Branch", "Add or edit areas, districts and stations (local churches). Tick 'National Headquarters' on the headquarters station."),
        ("churches", "BranchLeader", "Superintendents of areas and districts, pastors of stations and other officers."),
        ("churches", "Membership", "Who belongs to which unit, and who may manage it."),
    ]),
    ("leadership", "National councils", "The General Council and other councils, with photos and offices.", "👥", [
        ("leadership", "Council", "Create a council (for example the General Council)."),
        ("leadership", "CouncilMember", "Add or change the people and offices on a council."),
    ]),
    ("community", "Community life", "What happens in each unit: news, events and ministries.", "📣", [
        ("community", "Announcement", "News shown on a unit's page."),
        ("community", "Event", "Services, conferences and gatherings with RSVP."),
        ("community", "Ministry", "Choir, youth, women's fellowship and other groups."),
    ]),
    ("moderation", "Moderation", "Review what members post, and act on reports.", "🛡️", [
        ("community", "Report", "Posts, comments or prayer requests that members flagged."),
        ("community", "Post", "Board posts. Hide anything inappropriate."),
        ("community", "Comment", "Comments on board posts."),
        ("community", "PrayerRequest", "Prayer wall requests."),
    ]),
    ("media", "Sermons & media", "Messages and files members can watch, listen to or download.", "🎙️", [
        ("media_library", "Sermon", "Add or edit sermons, with a video link or an uploaded file."),
        ("media_library", "MediaAsset", "Uploaded audio, video, images and documents."),
    ]),
    ("history", "Church history", "The story of the church, with sources.", "📜", [
        ("history", "HistoricalEvent", "Timeline events. Publish them when ready."),
        ("history", "Era", "Periods that group events on the timeline."),
        ("history", "Figure", "People who shaped the church."),
        ("history", "Place", "Places connected to events."),
        ("history", "Document", "Creeds, letters and other primary texts."),
        ("history", "Source", "Books and references that back up the history."),
        ("history", "Tag", "Labels for finding related events."),
    ]),
    ("giving", "Giving", "Funds people can give to, and every gift received.", "💝", [
        ("giving", "Fund", "General fund, building fund and other giving purposes."),
        ("giving", "Donation", "Every gift. Records are kept as evidence and are not edited."),
    ]),
    ("news", "News", "Stories from inside the church and from the wider world, shown on the News page and home page.", "📰", [
        ("news", "NewsArticle", "Write, schedule, pin or hide news stories."),
    ]),
    ("books", "Books & shop", "The bookshop and library: books, e-books, daily devotional readings and orders.", "📚", [
        ("bookstore", "Book", "Add or edit books: price, stock, e-book file, cover and chapters to read online."),
        ("bookstore", "Order", "Orders from the shop. Mark bank transfers as paid and orders as sent."),
        ("bookstore", "DevotionalEntry", "Daily devotional readings (for example 'Life for You'), one per day."),
        ("bookstore", "Author", "Your ministers and writers from other churches."),
        ("bookstore", "Category", "Topics that group the books."),
    ]),
    ("website", "Website settings", "The site name, logo, announcement banner, contact details and social links.", "⚙️", [
        ("core", "SiteSettings", "Change the name, logo, banner and footer without touching any code."),
    ]),
    ("people", "People & access", "Accounts, who is an administrator, and roles.", "🔑", [
        ("accounts", "User", "Member accounts. Give someone administrator access here."),
        ("auth", "Group", "Roles such as Church administrators, Content editors and Moderators."),
    ]),
    ("messages", "Messages & notifications", "Behind-the-scenes records. You rarely need these.", "🔔", [
        ("realtime", "Notification", "Alerts shown to members."),
        ("realtime", "Conversation", "Chat conversations."),
        ("realtime", "Message", "Chat messages."),
        ("realtime", "PushSubscription", "Devices that receive push alerts."),
    ]),
]


class ChurchAdminSite(admin.AdminSite):
    site_header = "Church administration"
    site_title = "Church admin"
    index_title = "Dashboard"
    index_template = "admin/church/dashboard.html"

    # --- grouped navigation --------------------------------------------------
    def get_app_list(self, request, app_label=None):
        base = super().get_app_list(request, app_label)
        if app_label:  # Django's own per-app page: leave as is
            return base
        found = {}
        for app in base:
            for m in app["models"]:
                found[f"{app['app_label']}.{m['object_name']}"] = m
        index_url = reverse(f"{self.name}:index")
        sections, used = [], set()
        for slug, title, blurb, icon, items in SECTIONS:
            models = []
            for app_label_, name, help_ in items:
                key = f"{app_label_}.{name}"
                if key in found:
                    models.append({**found[key], "description": help_})
                    used.add(key)
            if models:
                sections.append({
                    "name": title, "description": blurb, "icon": icon, "slug": slug,
                    "app_label": slug, "app_url": f"{index_url}#{slug}",
                    "has_module_perms": True, "models": models,
                })
        leftovers = [m for k, m in found.items() if k not in used]
        if leftovers:  # anything added later still shows up
            sections.append({
                "name": "Other", "description": "Everything else.", "icon": "📦", "slug": "other",
                "app_label": "other", "app_url": f"{index_url}#other", "has_module_perms": True,
                "models": sorted(leftovers, key=lambda m: m["name"]),
            })
        return sections

    # --- dashboard -----------------------------------------------------------
    def index(self, request, extra_context=None):
        extra = {
            "quick_actions": self._quick_actions(request),
            "attention": self._attention(request),
            "stats": self._stats(),
            "checklist": self._checklist(request),
        }
        return super().index(request, {**extra, **(extra_context or {})})

    def _checklist(self, request):
        """A friendly 'set up your website' list: each step says whether it is done and links to where to do it."""
        from apps.churches.models import Branch
        from apps.core.models import SiteSettings
        from apps.leadership.models import Council, CouncilMember

        def url(name):
            try:
                return reverse(f"{self.name}:{name}")
            except NoReverseMatch:
                return ""

        st = SiteSettings.objects.filter(pk=1).first()
        levels = {}
        for lv in Branch.objects.filter(is_active=True).values_list("level", flat=True):
            levels[lv] = levels.get(lv, 0) + 1
        steps = [
            ("Add the church name and logo", bool(st and st.logo and st.church_name), url("core_sitesettings_changelist")),
            ("Add contact details for the footer", bool(st and (st.contact_email or st.contact_phone or st.address)), url("core_sitesettings_changelist")),
            ("Add the areas", levels.get(Branch.Level.AREA, 0) > 0, url("churches_branch_changelist") + "?level__exact=region"),
            ("Add the districts under their areas", levels.get(Branch.Level.DISTRICT, 0) > 0, url("churches_branch_changelist") + "?level__exact=district"),
            ("Add the stations under their districts", levels.get(Branch.Level.STATION, 0) > 0, url("churches_branch_changelist") + "?level__exact=local"),
            ("Mark which station is the National Headquarters", Branch.objects.filter(is_national_headquarters=True).exists(),
             url("churches_branch_changelist") + "?level__exact=local"),
            ("Create the General Council", Council.objects.filter(branch__isnull=True).exists(), url("leadership_council_changelist")),
            ("Add council members with photos", CouncilMember.objects.exclude(photo="").exists(), url("leadership_councilmember_changelist")),
        ]
        done = sum(1 for _, ok, _ in steps if ok)
        return {"steps": [{"label": l, "done": ok, "url": u} for l, ok, u in steps], "done": done,
                "total": len(steps), "percent": round(100 * done / len(steps))}

    def _quick_actions(self, request):
        wanted = [
            ("➕", "Add an area, district or station", "churches", "branch"),
            ("📰", "Post a news story", "news", "newsarticle"),
            ("📚", "Add a book", "bookstore", "book"),
            ("🌅", "Add a devotional reading", "bookstore", "devotionalentry"),
            ("🧑‍💼", "Add a superintendent or pastor", "churches", "branchleader"),
            ("👤", "Add a council member", "leadership", "councilmember"),
            ("📣", "Post an announcement", "community", "announcement"),
            ("📅", "Create an event", "community", "event"),
            ("🎙️", "Add a sermon", "media_library", "sermon"),
            ("📜", "Add a history event", "history", "historicalevent"),
            ("🔑", "Add a user", "accounts", "user"),
        ]
        if request.user.has_perm("core.change_sitesettings"):
            out_first = [{"icon": "⚙️", "label": "Change site name, logo or banner", "url": reverse(f"{self.name}:core_sitesettings_changelist")}]
        else:
            out_first = []
        out = list(out_first)
        for icon, label, app, model in wanted:
            if request.user.has_perm(f"{app}.add_{model}"):
                try:
                    out.append({"icon": icon, "label": label, "url": reverse(f"{self.name}:{app}_{model}_add")})
                except NoReverseMatch:
                    continue
        return out

    def _attention(self, request):
        """Things that need a human, with a count and a link. Only shown when there is something to do."""
        from apps.churches.models import Branch, BranchLeader
        from apps.community.models import Report
        from apps.giving.models import Donation
        from apps.history.models import HistoricalEvent

        u, items = request.user, []

        def add(perm, label, count, url_name, query):
            if count and u.has_perm(perm):
                try:
                    items.append({"label": label, "count": count, "url": reverse(f"{self.name}:{url_name}") + query})
                except NoReverseMatch:
                    pass

        add("community.view_report", "reports waiting for review", Report.objects.filter(resolved=False).count(),
            "community_report_changelist", "?resolved__exact=0")
        no_head = Branch.objects.filter(
            is_active=True, level__in=[Branch.Level.AREA, Branch.Level.DISTRICT]
        ).filter(~Exists(BranchLeader.objects.filter(branch=OuterRef("pk"), role="superintendent", is_current=True)))
        add("churches.view_branch", "areas/districts without a superintendent", no_head.count(),
            "churches_branch_changelist", "?level__in=region,district")
        add("history.view_historicalevent", "history events still in draft",
            HistoricalEvent.objects.exclude(status="published").count(),
            "history_historicalevent_changelist", "?status__exact=draft")
        from apps.bookstore.models import Order

        add("bookstore.view_order", "book orders waiting for payment", Order.objects.filter(status="pending").count(),
            "bookstore_order_changelist", "?status__exact=pending")
        add("bookstore.view_order", "paid orders to send out", Order.objects.filter(status="paid", items__fmt="print").distinct().count(),
            "bookstore_order_changelist", "?status__exact=paid")
        add("giving.view_donation", "donations still pending", Donation.objects.filter(status="pending").count(),
            "giving_donation_changelist", "?status__exact=pending")
        return items

    def _stats(self):
        from django.contrib.auth import get_user_model

        from apps.churches.models import Branch
        from apps.community.models import Event

        levels = {}
        for b in Branch.objects.filter(is_active=True).values_list("level", flat=True):
            levels[b] = levels.get(b, 0) + 1
        return [
            ("Areas", levels.get(Branch.Level.AREA, 0)),
            ("Districts", levels.get(Branch.Level.DISTRICT, 0)),
            ("Stations", levels.get(Branch.Level.STATION, 0)),
            ("Accounts", get_user_model().objects.filter(is_active=True).count()),
            ("Upcoming events", Event.objects.filter(starts_at__gte=timezone.now()).count()),
        ]
