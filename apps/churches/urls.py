from django.urls import path

from . import views

app_name = "churches"

urlpatterns = [
    path("", views.branch_list, name="list"),
    path("headquarters/", views.headquarters, name="headquarters"),
    path("areas/", views.unit_list, {"kind": "areas"}, name="areas"),
    path("districts/", views.unit_list, {"kind": "districts"}, name="districts"),
    path("stations/", views.unit_list, {"kind": "stations"}, name="stations"),
    path("<slug:slug>/", views.branch_detail, name="detail"),
    path("<slug:slug>/join/", views.join, name="join"),
    path("<slug:slug>/leave/", views.leave, name="leave"),
]
