from django.contrib import admin
from django.utils import timezone

from .models import Article, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.action(description="Publier les articles sélectionnés")
def publish_articles(modeladmin, request, queryset):
    queryset.update(status=Article.Status.PUBLISHED, published_at=timezone.now())


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "is_published_now",
        "published_at",
        "featured",
        "has_youtube",
        "created_at",
    )
    list_filter = ("category", "status", "featured", "tags", "published_at", "created_at")
    search_fields = ("title", "excerpt", "content", "sources")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "tags")
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")
    actions = [publish_articles]

    fieldsets = (
        ("Contenu principal", {"fields": ("title", "slug", "excerpt", "cover_image")}),
        ("Contenu de l'article", {"fields": ("content_stream",)}),
        ("Compatibilité (optionnel)", {"classes": ("collapse",), "fields": ("content",)}),
        ("Classement", {"fields": ("category", "tags")}),
        ("Publication", {"fields": ("status", "featured", "published_at")}),
        ("Médias & sources", {"fields": ("youtube_url", "sources")}),
        ("Métadonnées", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(boolean=True, description="Publié ?")
    def is_published_now(self, obj):
        return obj.status == Article.Status.PUBLISHED and obj.published_at and obj.published_at <= timezone.now()

    @admin.display(boolean=True, description="YouTube")
    def has_youtube(self, obj):
        return bool(obj.youtube_url)


# Resource model intentionally not exposed in admin for current V1 scope.
