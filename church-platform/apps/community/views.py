"""Branch community: events, announcements, board, groups, prayer wall, moderation.

Visibility
  * Overview, events, announcements and sermons are public.
  * Board, groups and prayer wall are for members of the branch (and its leaders / central staff).
  * Leaders (see apps.core.permissions.can_manage_branch) can post announcements and events and
    moderate content.
"""
import logging

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.churches.models import Branch, Membership
from apps.core.permissions import can_manage_branch
from apps.realtime.tasks import notify_users

from .forms import AnnouncementForm, CommentForm, EventForm, PostForm, PrayerForm, ReportForm
from .models import (
    Announcement,
    Comment,
    Event,
    EventRSVP,
    Ministry,
    Post,
    PrayerRequest,
    Report,
)

logger = logging.getLogger(__name__)
PAGE_SIZE = 15


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def get_branch(slug):
    return get_object_or_404(Branch.objects.select_related("parent"), slug=slug, is_active=True)


def is_member(user, branch):
    return user.is_authenticated and Membership.objects.filter(user=user, branch=branch).exists()


def _ctx(request, branch, active, **extra):
    return {
        "branch": branch,
        "active": active,
        "can_manage": can_manage_branch(request.user, branch),
        "is_member": is_member(request.user, branch),
        **extra,
    }


def members_only(request, branch):
    """Return a response when the visitor may not see member-only pages, else None."""
    user = request.user
    if user.is_authenticated and (is_member(user, branch) or can_manage_branch(user, branch)):
        return None
    status = 403 if user.is_authenticated else 200
    return render(request, "community/members_only.html", _ctx(request, branch, "members"), status=status)


def manager_gate(request, branch):
    """Return a response unless the user may manage this branch."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not can_manage_branch(request.user, branch):
        raise PermissionDenied
    return None


def _back(request, default):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(nxt)
    return redirect(default)


def _get_target(kind, pk, branch):
    if kind == "post":
        return get_object_or_404(Post, pk=pk, branch=branch)
    if kind == "comment":
        return get_object_or_404(Comment, pk=pk, post__branch=branch)
    if kind == "prayer":
        return get_object_or_404(PrayerRequest, pk=pk, branch=branch)
    raise Http404


def _queue_notifications(user_ids, title, body="", url=""):
    """Never let a notification problem break the action that triggered it."""
    user_ids = list(user_ids)
    if not user_ids:
        return
    try:
        notify_users.delay(user_ids, title, body, url)
    except Exception:  # noqa: BLE001
        logger.exception("Could not queue notifications")


def _leader_ids(branch, exclude_user=None):
    qs = Membership.objects.filter(
        branch=branch, role__in=[Membership.Role.LEADER, Membership.Role.ADMIN]
    )
    if exclude_user is not None:
        qs = qs.exclude(user=exclude_user)
    return list(qs.values_list("user_id", flat=True).distinct())


def _form_page(request, branch, active, form, title, submit, multipart=False):
    return render(
        request,
        "churches/form_page.html",
        _ctx(request, branch, active, form=form, title=title, submit=submit, multipart=multipart),
    )


# --------------------------------------------------------------------------
# events & announcements (public pages, leader tools)
# --------------------------------------------------------------------------
def events(request, slug):
    branch = get_branch(slug)
    past = request.GET.get("past") == "1"
    now = timezone.now()
    qs = Event.objects.filter(branch=branch)
    qs = qs.filter(starts_at__lt=now).order_by("-starts_at") if past else qs.filter(starts_at__gte=now)
    qs = qs.annotate(going=Count("rsvps", filter=Q(rsvps__status=EventRSVP.Status.GOING)))
    items = list(qs[:50])

    mine = {}
    if request.user.is_authenticated and items:
        mine = dict(
            EventRSVP.objects.filter(user=request.user, event__in=items).values_list("event_id", "status")
        )
    for e in items:
        e.my_status = mine.get(e.pk)
        e.is_full = e.capacity is not None and e.going >= e.capacity
    return render(request, "community/events.html", _ctx(request, branch, "events", events=items, past=past))


@require_POST
def event_rsvp(request, slug, event_id):
    branch = get_branch(slug)
    if not request.user.is_authenticated:
        return redirect_to_login(request.POST.get("next") or reverse("community:events", args=[slug]))
    event = get_object_or_404(Event, pk=event_id, branch=branch)
    status = request.POST.get("status", EventRSVP.Status.GOING)
    if status not in EventRSVP.Status.values:
        messages.error(request, "That response isn't valid.")
        return _back(request, reverse("community:events", args=[slug]))
    if status == EventRSVP.Status.GOING and event.capacity is not None:
        going = event.rsvps.filter(status=EventRSVP.Status.GOING).exclude(user=request.user).count()
        if going >= event.capacity:
            messages.error(request, "Sorry, this event is full.")
            return _back(request, reverse("community:events", args=[slug]))
    EventRSVP.objects.update_or_create(event=event, user=request.user, defaults={"status": status})
    messages.success(request, "Your response was saved.")
    return _back(request, reverse("community:events", args=[slug]))


def event_create(request, slug):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.branch, event.created_by = branch, request.user
        event.save()
        member_ids = Membership.objects.filter(branch=branch).exclude(user=request.user).values_list("user_id", flat=True)
        _queue_notifications(member_ids, f"New event: {event.title}", branch.name,
                             reverse("community:events", args=[slug]))
        messages.success(request, "Event created.")
        return redirect("community:events", slug=slug)
    return _form_page(request, branch, "events", form, "New event", "Create event")


def announcement_create(request, slug):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.branch, obj.author = branch, request.user
        obj.save()
        member_ids = Membership.objects.filter(branch=branch).exclude(user=request.user).values_list("user_id", flat=True)
        _queue_notifications(member_ids, obj.title, branch.name, branch.get_absolute_url())
        messages.success(request, "Announcement posted.")
        return redirect(branch)
    return _form_page(request, branch, "overview", form, "New announcement", "Post announcement")


# --------------------------------------------------------------------------
# community board
# --------------------------------------------------------------------------
def board(request, slug):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    manage = can_manage_branch(request.user, branch)
    posts = Post.objects.filter(branch=branch).select_related("author")
    if not manage:
        posts = posts.filter(is_hidden=False)
    posts = posts.annotate(n_comments=Count("comments", filter=Q(comments__is_hidden=False)))
    page = Paginator(posts, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "community/board.html", _ctx(request, branch, "board", page=page))


def post_create(request, slug):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    form = PostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.branch, post.author = branch, request.user
        post.save()
        messages.success(request, "Your post is up.")
        return redirect("community:post_detail", slug=slug, post_id=post.pk)
    return _form_page(request, branch, "board", form, "New post", "Publish")


def post_detail(request, slug, post_id):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    manage = can_manage_branch(request.user, branch)
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id, branch=branch)
    if post.is_hidden and not manage:
        raise Http404

    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.post, comment.author = post, request.user
        comment.save()
        if post.author_id != request.user.pk:
            _queue_notifications([post.author_id], "New comment on your post", post.title,
                                 reverse("community:post_detail", args=[slug, post.pk]))
        return redirect("community:post_detail", slug=slug, post_id=post.pk)

    comments = post.comments.select_related("author")
    if not manage:
        comments = comments.filter(is_hidden=False)
    return render(
        request, "community/post_detail.html",
        _ctx(request, branch, "board", post=post, comments=comments, form=form),
    )


# --------------------------------------------------------------------------
# groups (ministries)
# --------------------------------------------------------------------------
def groups(request, slug):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    items = list(Ministry.objects.filter(branch=branch).annotate(n_members=Count("members")))
    mine = set(request.user.ministries.filter(branch=branch).values_list("pk", flat=True))
    for g in items:
        g.joined = g.pk in mine
    return render(request, "community/groups.html", _ctx(request, branch, "groups", groups=items))


@require_POST
def group_join(request, slug, ministry_slug):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    ministry = get_object_or_404(Ministry, branch=branch, slug=ministry_slug)
    ministry.members.add(request.user)
    messages.success(request, f"You joined {ministry.name}.")
    return redirect("community:groups", slug=slug)


@require_POST
def group_leave(request, slug, ministry_slug):
    branch = get_branch(slug)
    ministry = get_object_or_404(Ministry, branch=branch, slug=ministry_slug)
    if request.user.is_authenticated:
        ministry.members.remove(request.user)
        messages.success(request, f"You left {ministry.name}.")
    return redirect("community:groups", slug=slug)


# --------------------------------------------------------------------------
# prayer wall
# --------------------------------------------------------------------------
def prayer(request, slug):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    manage = can_manage_branch(request.user, branch)

    form = PrayerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.branch, obj.author = branch, request.user
        obj.save()
        # Leaders are told a request exists; the text itself stays on the wall.
        _queue_notifications(_leader_ids(branch, exclude_user=request.user),
                             "New prayer request", branch.name,
                             reverse("community:prayer", args=[slug]))
        messages.success(request, "Your prayer request was shared. We're praying with you.")
        return redirect("community:prayer", slug=slug)

    items = PrayerRequest.objects.filter(branch=branch).select_related("author")
    if not manage:
        items = items.filter(is_hidden=False)
    page = Paginator(items, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "community/prayer.html", _ctx(request, branch, "prayer", page=page, form=form))


@require_POST
def prayer_answered(request, slug, pk):
    branch = get_branch(slug)
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    obj = get_object_or_404(PrayerRequest, pk=pk, branch=branch, author=request.user)
    obj.is_answered = not obj.is_answered
    obj.save(update_fields=["is_answered", "updated_at"])
    return _back(request, reverse("community:prayer", args=[slug]))


# --------------------------------------------------------------------------
# moderation
# --------------------------------------------------------------------------
@require_POST
def toggle_hidden(request, slug, kind, pk):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    obj = _get_target(kind, pk, branch)
    obj.is_hidden = not obj.is_hidden
    obj.save(update_fields=["is_hidden", "updated_at"])
    messages.success(request, "Hidden from members." if obj.is_hidden else "Visible to members again.")
    return _back(request, reverse("community:board", args=[slug]))


@require_POST
def report(request, slug, kind, pk):
    branch = get_branch(slug)
    blocked = members_only(request, branch)
    if blocked:
        return blocked
    target = _get_target(kind, pk, branch)
    form = ReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please say briefly what the problem is.")
        return _back(request, reverse("community:board", args=[slug]))
    if Report.objects.filter(reporter=request.user, resolved=False, **{kind: target}).exists():
        messages.info(request, "You've already reported this; leaders will review it.")
    else:
        Report.objects.create(branch=branch, reporter=request.user,
                              reason=form.cleaned_data["reason"], **{kind: target})
        _queue_notifications(_leader_ids(branch, exclude_user=request.user),
                             "Content reported", branch.name,
                             reverse("community:moderation", args=[slug]))
        messages.success(request, "Thank you. The branch leaders have been notified.")
    return _back(request, reverse("community:board", args=[slug]))


def moderation(request, slug):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    show_all = request.GET.get("all") == "1"
    reports = Report.objects.filter(branch=branch).select_related("reporter", "post", "comment", "prayer")
    if not show_all:
        reports = reports.filter(resolved=False)
    return render(
        request, "community/moderation.html",
        _ctx(request, branch, "manage", reports=reports, show_all=show_all),
    )


@require_POST
def resolve_report(request, slug, report_id, action):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    if action not in ("hide", "dismiss"):
        raise Http404
    rep = get_object_or_404(Report, pk=report_id, branch=branch)
    if action == "hide" and rep.target is not None:
        rep.target.is_hidden = True
        rep.target.save(update_fields=["is_hidden", "updated_at"])
    rep.resolved, rep.resolved_by = True, request.user
    rep.save(update_fields=["resolved", "resolved_by", "updated_at"])
    messages.success(request, "Report closed.")
    return redirect("community:moderation", slug=slug)
