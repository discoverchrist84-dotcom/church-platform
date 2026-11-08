from datetime import date

from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth

from apps.churches.models import Branch
from apps.core.permissions import can_manage_branch

from .models import MediaAsset, Sermon

router = Router()

ALLOWED_PREFIXES = {
    "audio/": MediaAsset.Kind.AUDIO,
    "video/": MediaAsset.Kind.VIDEO,
    "image/": MediaAsset.Kind.IMAGE,
}
ALLOWED_DOCUMENTS = {"application/pdf"}


class AssetOut(Schema):
    id: int
    original_name: str
    kind: str
    size: int
    url: str

    @staticmethod
    def resolve_url(obj):
        return obj.file.url


class SermonOut(Schema):
    id: int
    title: str
    speaker: str
    preached_on: date
    scripture: str
    description: str
    video_url: str
    audio_url: str | None = None

    @staticmethod
    def resolve_audio_url(obj):
        return obj.asset.file.url if obj.asset_id else None


def classify_upload(content_type: str):
    for prefix, kind in ALLOWED_PREFIXES.items():
        if content_type.startswith(prefix):
            return kind
    if content_type in ALLOWED_DOCUMENTS:
        return MediaAsset.Kind.DOCUMENT
    return None


@router.post("/upload", response={201: AssetOut}, auth=django_auth)
def upload(request, file: UploadedFile = File(...), branch_slug: str | None = Form(None)):
    """Upload a file through the server.

    Fine for images/PDFs and modest audio. For large sermon video, switch to
    direct-to-storage presigned uploads (see README roadmap).
    """
    kind = classify_upload(file.content_type or "")
    if kind is None:
        raise HttpError(415, "Unsupported file type.")
    if file.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HttpError(413, f"File exceeds {settings.MAX_UPLOAD_MB} MB.")

    branch = None
    if branch_slug:
        branch = get_object_or_404(Branch, slug=branch_slug)
        if not can_manage_branch(request.user, branch):
            raise HttpError(403, "Only branch leaders can upload to a branch.")

    asset = MediaAsset.objects.create(
        owner=request.user,
        branch=branch,
        file=file,
        kind=kind,
        original_name=file.name[:255],
        content_type=file.content_type or "",
        size=file.size,
    )
    return 201, asset


@router.get("/branches/{slug}/sermons", response=list[SermonOut])
def list_sermons(request, slug: str):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    return Sermon.objects.filter(branch=branch, is_published=True).select_related("asset")[:50]
