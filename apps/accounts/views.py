from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("core:home")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    """Everything personal in one place: books and orders, cart, notifications, giving, my units."""
    user = request.user
    from apps.bookstore.services import cart_count

    return render(request, "accounts/dashboard.html", {
        "memberships": user.memberships.select_related("branch").order_by("-is_primary", "branch__name"),
        "orders": user.book_orders.order_by("-created_at")[:3],
        "order_count": user.book_orders.count(),
        "donation_count": user.donations.count(),
        "unread": user.notifications.filter(is_read=False).count(),
        "cart_items": cart_count(request),
    })
