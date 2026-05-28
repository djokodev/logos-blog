from django.urls import path

from .views import AboutView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("a-propos/", AboutView.as_view(), name="about"),
]
