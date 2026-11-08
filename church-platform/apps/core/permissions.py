"""Role checks shared by the API and views.

Hierarchy:
  * central admins  -> users with is_staff / is_superuser (manage everything)
  * branch admins   -> Membership(role=admin) on a branch or any ancestor of it
  * branch leaders  -> Membership(role=leader|admin) on that exact branch
"""
from apps.churches.models import Membership


def is_central_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def can_manage_branch(user, branch) -> bool:
    """May create announcements/events/sermons for this branch."""
    if not (user and user.is_authenticated):
        return False
    if is_central_admin(user):
        return True
    branch_ids = [branch.pk] + [b.pk for b in branch.ancestors()]
    memberships = Membership.objects.filter(user=user, branch_id__in=branch_ids)
    for m in memberships:
        if m.role == Membership.Role.ADMIN:
            return True
        if m.role == Membership.Role.LEADER and m.branch_id == branch.pk:
            return True
    return False
