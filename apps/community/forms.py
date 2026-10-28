from django import forms

from .models import Announcement, Comment, Event, Post, PrayerRequest

DT_FORMAT = "%Y-%m-%dT%H:%M"
DT_INPUTS = [DT_FORMAT, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("title", "body")
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}
        labels = {"body": "Message"}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}
        labels = {"body": "Add a comment"}


class PrayerForm(forms.ModelForm):
    class Meta:
        model = PrayerRequest
        fields = ("body", "is_anonymous")
        widgets = {"body": forms.Textarea(attrs={"rows": 4, "placeholder": "How can we pray with you?"})}
        labels = {"body": "Prayer request", "is_anonymous": "Share anonymously"}


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("title", "body", "is_pinned")
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}
        labels = {"is_pinned": "Pin to the top"}


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ("title", "description", "location", "starts_at", "ends_at", "capacity")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
        }
        help_texts = {"capacity": "Leave empty for no limit."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("starts_at", "ends_at"):
            self.fields[name].input_formats = DT_INPUTS

    def clean(self):
        data = super().clean()
        start, end = data.get("starts_at"), data.get("ends_at")
        if start and end and end <= start:
            self.add_error("ends_at", "The end time must be after the start.")
        return data


class ReportForm(forms.Form):
    reason = forms.CharField(min_length=3, max_length=500)
