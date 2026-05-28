from django.urls import path

from . import views

urlpatterns = [
    path("", views.article_list, name="article_list"),
    path("categorie/<slug:slug>/", views.category_detail, name="category_detail"),
    path("preview/<int:pk>/", views.article_preview, name="article_preview"),
    path("<slug:slug>/", views.article_detail, name="article_detail"),
]
