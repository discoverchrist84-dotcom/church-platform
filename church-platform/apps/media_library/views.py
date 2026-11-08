from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.http import urlencode
from django.shortcuts import redirect, render

from apps.community.views import _ctx, get_branch, manager_gate

from .api import classify_upload
from .embeds import embed_url
from .forms import SermonForm
from .models import MediaAsset, Sermon


def sermons(request, slug):
    branch = get_branch(slug)
    q = request.GET.get("q", "").strip()
    qs = Sermon.objects.filter(branch=branch, is_published=True).select_related("asset")
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(speaker__icontains=q) | qs.filter(scripture__icontains=q)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    for s in page:
        s.embed = embed_url(s.video_url)
    return render(request, "media_library/sermons.html", _ctx(request, branch, "sermons", page=page, q=q, qs=urlencode({"q": q}) if q else ""))


def sermon_create(request, slug):
    branch = get_branch(slug)
    blocked = manager_gate(request, branch)
    if blocked:
        return blocked
    form = SermonForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        sermon = form.save(commit=False)
        sermon.branch = branch
        upload = form.cleaned_data.get("media_file")
        if upload:
            sermon.asset = MediaAsset.objects.create(
                owner=request.user,
                branch=branch,
                file=upload,
                kind=classify_upload(upload.content_type or ""),
                original_name=upload.name[:255],
                content_type=upload.content_type or "",
                size=upload.size,
            )
        sermon.save()
        messages.success(request, "Sermon added.")
        return redirect("media_library:sermons", slug=slug)
    return render(
        request,
        "churches/form_page.html",
        _ctx(request, branch, "sermons", form=form, title="Add a sermon", submit="Save sermon", multipart=True),
    )
