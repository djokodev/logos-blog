from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Article, Category, Tag


class ArticleSnippetViewSet(SnippetViewSet):
    model = Article
    menu_label = "Articles"
    menu_name = "logos_articles"
    menu_order = 200
    icon = "doc-full-inverse"
    add_to_admin_menu = True
    list_display = ("title", "category", "status", "featured", "published_at", "updated_at")
    list_filter = ("status", "featured", "category")
    search_fields = ("title", "excerpt", "content", "sources")
    panels = [
        TitleFieldPanel("title", targets=["slug"]),
        FieldPanel("slug"),
        FieldPanel("excerpt"),
        FieldPanel("cover_image"),
        FieldPanel("content_stream"),
        FieldPanel("category"),
        FieldPanel("tags"),
        FieldPanel("youtube_url"),
        FieldPanel("sources"),
        FieldPanel("status"),
        FieldPanel("featured"),
        FieldPanel("published_at"),
    ]


class CategorySnippetViewSet(SnippetViewSet):
    model = Category
    menu_label = "Catégories"
    menu_name = "logos_categories"
    menu_order = 210
    icon = "folder-open-inverse"
    add_to_admin_menu = True
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "description")
    panels = [TitleFieldPanel("name", targets=["slug"]), FieldPanel("slug"), FieldPanel("description")]


class TagSnippetViewSet(SnippetViewSet):
    model = Tag
    menu_label = "Tags"
    menu_name = "logos_tags"
    menu_order = 220
    icon = "tag"
    add_to_admin_menu = True
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name",)
    panels = [TitleFieldPanel("name", targets=["slug"]), FieldPanel("slug")]


register_snippet(ArticleSnippetViewSet)
register_snippet(CategorySnippetViewSet)
register_snippet(TagSnippetViewSet)
