from .models import Membership


def join_branch(user, branch):
    """Add `user` to `branch`. The first branch someone joins becomes their primary one."""
    membership, created = Membership.objects.get_or_create(user=user, branch=branch)
    if not Membership.objects.filter(user=user, is_primary=True).exists():
        membership.is_primary = True
        membership.save(update_fields=["is_primary", "updated_at"])
    return membership, created


def leave_branch(user, branch):
    deleted, _ = Membership.objects.filter(user=user, branch=branch).delete()
    return bool(deleted)
