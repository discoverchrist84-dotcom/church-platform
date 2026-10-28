from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image


class Branch(TimeStampedModel):
    """A unit of the church. Strict chain of command:

        Area > District > Station

    A station (a local church) belongs to one district and a district to one area. Areas are the
    top level. The National Headquarters is not a separate level: it is one station (tick
    "National Headquarters" on it) that sits in its own district and area like any other.
    Areas and districts are led by superintendents (see BranchLeader).
    (The stored values "region" and "local" are kept from earlier versions so existing data
    still works; they are now shown as "Area" and "Station".)
    """

    class Level(models.TextChoices):
        AREA = "region", "Area"
        DISTRICT = "district", "District"
        STATION = "local", "Station"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.STATION)
    description = models.TextField(blank=True)
    service_times = models.TextField(blank=True, help_text="e.g. Sunday 9:00 & 11:00")

    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField("state / region", max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    logo = models.ImageField(upload_to="branches/logos/", blank=True, validators=[validate_image], help_text="Square logo, JPG or PNG. Large phone photos are resized automatically.")
    cover = models.ImageField(upload_to="branches/covers/", blank=True, validators=[validate_image], help_text="Wide picture shown at the top of the page, resized automatically.")
    is_active = models.BooleanField(default=True)
    serial = models.PositiveIntegerField(
        "register number", null=True, blank=True,
        help_text="The unit's number in the church's printed register. Units are listed in this order (then by name).",
    )
    is_national_headquarters = models.BooleanField(
        "National Headquarters", default=False,
        help_text="Tick on the one station that is the National Headquarters. Only one station can have this.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "branches"
        constraints = [
            models.UniqueConstraint(
                fields=["is_national_headquarters"], condition=models.Q(is_national_headquarters=True),
                name="only_one_national_headquarters",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "branch"
            slug, n = base, 2
            while Branch.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("churches:detail", args=[self.slug])

    def clean(self):
        """Enforce Area > District > Station (runs in the admin and in forms)."""
        super().clean()
        L = self.Level
        errors = {}
        label = self.get_level_display().lower()
        if self.level == L.AREA:
            if self.parent_id:
                errors["parent"] = "An area is the top level of the structure, so it does not sit under another unit. Leave 'parent' empty."
        else:
            need = PARENT_LEVEL[self.level]
            if not self.parent_id:
                errors["parent"] = f"A {label} must be allocated to a {L(need).label.lower()}."
            elif self.parent.level != need:
                errors["parent"] = (
                    f"A {label} belongs under a {L(need).label.lower()}, "
                    f"not a {self.parent.get_level_display().lower()}."
                )
            elif self.pk and (self.parent_id == self.pk or self.pk in [a.pk for a in self.parent.ancestors()]):
                errors["parent"] = "A unit cannot be placed under itself or one of its own sub-units."
        if self.is_national_headquarters:
            if self.level != L.STATION:
                errors["is_national_headquarters"] = "The National Headquarters is a station (a local church). Set the type to Station first."
            elif Branch.objects.filter(is_national_headquarters=True).exclude(pk=self.pk).exists():
                errors["is_national_headquarters"] = "Another station is already the National Headquarters. Untick it there first."
        if errors:
            raise ValidationError(errors)

    LEVEL_NOTE = {"region": "Area", "district": "District", "local": "Local church"}

    @property
    def level_note(self):
        if self.is_national_headquarters:
            return "National Headquarters"
        return self.LEVEL_NOTE.get(self.level, "")

    # --- leaders -----------------------------------------------------------
    def _current_leaders(self):
        cached = getattr(self, "current_leaders", None)  # set by Prefetch(to_attr=...) in list views
        if cached is not None:
            return cached
        return list(self.leaders.filter(is_current=True))

    @property
    def superintendent(self):
        """The serving superintendent (areas and districts) or pastor-in-charge (stations)."""
        for role in (BranchLeader.Role.SUPERINTENDENT, BranchLeader.Role.PASTOR):
            for leader in self._current_leaders():
                if leader.role == role:
                    return leader
        return None

    @property
    def head_title(self):
        return {"region": "Area Superintendent", "district": "District Superintendent", "local": "Pastor-in-charge"}.get(self.level, "")

    @property
    def breadcrumbs(self):
        """Ancestors from the top (its area) down to this unit's parent."""
        return list(reversed(self.ancestors()))

    @property
    def child_level(self):
        """The level directly below this one (None for a station)."""
        return CHILD_LEVEL.get(self.level)

    @property
    def child_label_plural(self) -> str:
        return {"region": "Districts", "district": "Stations"}.get(self.level, "")

    def descendants(self):
        """Every active unit below this one (a handful of queries, not one per level)."""
        out, frontier = [], [self.pk]
        while frontier:
            kids = list(Branch.objects.filter(parent_id__in=frontier, is_active=True))
            out.extend(kids)
            frontier = [k.pk for k in kids]
        return out

    def counts(self) -> dict:
        """e.g. {"areas": 3, "districts": 9, "stations": 41} for the levels below this one."""
        below = self.descendants()
        names = {"region": "areas", "district": "districts", "local": "stations"}
        result = {}
        for lvl, label in names.items():
            n = sum(1 for b in below if b.level == lvl)
            if n:
                result[label] = n
        return result

    def ancestors(self):
        """Parents from nearest to root. Guards against accidental cycles."""
        seen, node, out = {self.pk}, self.parent, []
        while node is not None and node.pk not in seen:
            out.append(node)
            seen.add(node.pk)
            node = node.parent
        return out


class BranchLeader(TimeStampedModel):
    """Someone who leads a unit: the superintendent of an area or district, the pastor of a station,
    or other officers. (National councils and their offices live in apps.leadership.)"""

    class Role(models.TextChoices):
        SUPERINTENDENT = "superintendent", "Superintendent"
        ASSISTANT = "assistant", "Assistant superintendent"
        PASTOR = "pastor", "Pastor-in-charge"
        SECRETARY = "secretary", "Secretary"
        TREASURER = "treasurer", "Treasurer"
        OTHER = "other", "Other officer"

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="leaders")
    name = models.CharField(max_length=160)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SUPERINTENDENT)
    title = models.CharField(
        max_length=120, blank=True, help_text="Optional custom title, e.g. 'Rev. Dr.' or 'Deputy Superintendent'."
    )
    photo = models.ImageField(upload_to="branches/leaders/", blank=True, validators=[validate_image], help_text="Square or portrait photo, JPG or PNG. Large phone photos are resized automatically.")
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    show_contact = models.BooleanField(default=False, help_text="Show phone/email publicly. Off by default.")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leader_roles",
        help_text="Optional: link their account. A linked superintendent/pastor can then manage this unit and everything below it.",
    )
    term_start = models.PositiveSmallIntegerField("serving since (year)", null=True, blank=True)
    is_current = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "role", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch"],
                condition=models.Q(role="superintendent", is_current=True),
                name="one_current_superintendent_per_unit",
            ),
        ]

    def __str__(self):
        return f"{self.name}: {self.display_title} ({self.branch})"

    @property
    def display_title(self):
        if self.title:
            return self.title
        if self.role == self.Role.SUPERINTENDENT:
            return {"region": "Area Superintendent", "district": "District Superintendent"}.get(
                self.branch.level, "Superintendent"
            )
        return self.get_role_display()

    @property
    def initials(self):
        parts = [p for p in self.name.replace(".", " ").split() if p[:1].isalpha()]
        return "".join(p[0] for p in (parts[:1] + parts[-1:] if len(parts) > 1 else parts[:1])).upper()

    def clean(self):
        super().clean()
        if self.role == self.Role.SUPERINTENDENT and self.branch_id:
            if self.branch.level not in (Branch.Level.AREA, Branch.Level.DISTRICT):
                raise ValidationError({"role": "Only areas and districts have superintendents. Use Pastor-in-charge for a station."})
            if self.is_current and BranchLeader.objects.filter(
                branch=self.branch, role=self.Role.SUPERINTENDENT, is_current=True
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    {"is_current": "This unit already has a serving superintendent. Untick 'current' on the previous one first."}
                )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # A linked superintendent / pastor becomes admin of their unit (and so of everything below it).
        if self.user_id and self.is_current and self.role in (self.Role.SUPERINTENDENT, self.Role.PASTOR):
            m, created = Membership.objects.get_or_create(
                user_id=self.user_id, branch=self.branch, defaults={"role": Membership.Role.ADMIN}
            )
            if not created and m.role != Membership.Role.ADMIN:
                m.role = Membership.Role.ADMIN
                m.save(update_fields=["role", "updated_at"])


PARENT_LEVEL = {
    Branch.Level.DISTRICT: Branch.Level.AREA,
    Branch.Level.STATION: Branch.Level.DISTRICT,
}
CHILD_LEVEL = {
    Branch.Level.AREA: Branch.Level.DISTRICT,
    Branch.Level.DISTRICT: Branch.Level.STATION,
}


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        LEADER = "leader", "Leader"
        ADMIN = "admin", "Branch admin"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    is_primary = models.BooleanField(
        default=False, help_text="The branch this person primarily attends."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "branch"], name="unique_user_branch")
        ]

    def __str__(self):
        return f"{self.user} @ {self.branch} ({self.role})"
