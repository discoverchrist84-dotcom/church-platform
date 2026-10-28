from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.security import django_auth

from .models import Branch
from .services import join_branch, leave_branch

router = Router()


class BranchOut(Schema):
    id: int
    name: str
    slug: str
    level: str
    parent_slug: str | None = None
    description: str
    service_times: str
    address: str
    city: str
    region: str
    country: str
    latitude: float | None = None
    longitude: float | None = None
    phone: str
    email: str
    website: str

    @staticmethod
    def resolve_parent_slug(obj):
        return obj.parent.slug if obj.parent_id else None


@router.get("/", response=list[BranchOut])
def list_branches(request, q: str | None = None, country: str | None = None):
    qs = Branch.objects.filter(is_active=True).select_related("parent")
    if q:
        qs = qs.filter(name__icontains=q)
    if country:
        qs = qs.filter(country__iexact=country)
    return qs


@router.get("/{slug}", response=BranchOut)
def get_branch(request, slug: str):
    return get_object_or_404(Branch.objects.select_related("parent"), slug=slug, is_active=True)


@router.post("/{slug}/join", auth=django_auth)
def join_branch_endpoint(request, slug: str):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    _, created = join_branch(request.user, branch)
    return {"joined": True, "created": created}


@router.post("/{slug}/leave", auth=django_auth)
def leave_branch_endpoint(request, slug: str):
    branch = get_object_or_404(Branch, slug=slug)
    return {"left": leave_branch(request.user, branch)}
