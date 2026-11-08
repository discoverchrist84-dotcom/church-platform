from django.urls import path

from . import views

app_name = "giving"

urlpatterns = [
    path("", views.give, name="give"),
    path("thanks/", views.thanks, name="thanks"),
    path("history/", views.history, name="history"),
    path("dev-pay/<uuid:reference>/", views.dev_pay, name="dev_pay"),
]
