from django.urls import path

from . import views

app_name = "bookstore"

urlpatterns = [
    path("", views.book_list, name="list"),
    path("devotional/", views.devotional_today, name="devotional"),
    path("devotional/archive/", views.devotional_archive, name="devotional_archive"),
    path("devotional/<str:day>/", views.devotional_day, name="devotional_day"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<slug:slug>/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("library/", views.library, name="library"),
    path("orders/<uuid:reference>/", views.order_detail, name="order"),
    path("orders/<uuid:reference>/dev-pay/", views.dev_pay, name="dev_pay"),
    path("download/<slug:slug>/", views.download, name="download"),
    path("<slug:slug>/", views.book_detail, name="detail"),
    path("<slug:slug>/read/<int:number>/", views.read, name="read"),
]
