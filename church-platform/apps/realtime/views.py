from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notifications(request):
    page = Paginator(Notification.objects.filter(user=request.user), 25).get_page(request.GET.get("page"))
    return render(request, "realtime/notifications.html", {"page": page})


@login_required
def open_notification(request, pk):
    """Mark one notification read, then continue to the page it points at."""
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=["is_read", "updated_at"])
    target = note.url
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(reverse("realtime:list"))


@login_required
@require_POST
def read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("realtime:list")
