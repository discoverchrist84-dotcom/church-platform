from django import forms
from django.conf import settings

from .api import classify_upload
from .models import Sermon


class SermonForm(forms.ModelForm):
    media_file = forms.FileField(
        required=False,
        label="Audio, video or PDF file",
        help_text="Optional. You can also just paste a YouTube or Vimeo link below.",
    )

    class Meta:
        model = Sermon
        fields = ("title", "speaker", "preached_on", "scripture", "description", "video_url", "is_published")
        widgets = {
            "preached_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {"video_url": "YouTube / Vimeo link", "is_published": "Publish now"}

    def clean_media_file(self):
        f = self.cleaned_data.get("media_file")
        if not f:
            return f
        if classify_upload(f.content_type or "") is None:
            raise forms.ValidationError("Please upload an audio, video, image or PDF file.")
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"That file is larger than {settings.MAX_UPLOAD_MB} MB.")
        return f
