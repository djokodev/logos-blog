from datetime import timedelta

from django.db.models import Count, Q
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.panels import (
    FieldPanel,
    HelpPanel,
    MultiFieldPanel,
    ObjectList,
    PublishingPanel,
    TabbedInterface,
    TitleFieldPanel,
)
from wagtail.admin.ui.components import Component
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Article, ArticleView, Category, Tag

EDITOR_HELP = """
<p><strong>Astuces d'écriture</strong> : dans un bloc <em>Texte</em>, tapez <kbd>/</kbd> en début de ligne pour
insérer un titre, une liste, une citation, une image… Sélectionnez du texte pour le mettre en forme
(gras, italique, lien). <kbd>Ctrl/⌘ + B</kbd> gras, <kbd>Ctrl/⌘ + I</kbd> italique, <kbd>Ctrl/⌘ + K</kbd> lien.</p>
<p>Le bouton <strong>Aperçu</strong> (en haut à droite) affiche l'article en direct pendant que vous écrivez.
<strong>Enregistrer le brouillon</strong> ne change rien sur le site public ; seul <strong>Publier</strong> le met en ligne.</p>
"""


class ArticleSnippetViewSet(SnippetViewSet):
    model = Article
    menu_label = "Articles"
    menu_name = "logos_articles"
    menu_order = 200
    icon = "doc-full-inverse"
    add_to_admin_menu = True
    list_display = ("title", "category", "published_at", "view_count", "featured")
    list_filter = ("live", "featured", "category")
    search_fields = ("title", "excerpt")
    ordering = ("-published_at",)
    list_per_page = 30

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    TitleFieldPanel("title", targets=["slug"], classname="title"),
                    FieldPanel("excerpt"),
                    FieldPanel("cover"),
                    HelpPanel(content=EDITOR_HELP),
                    FieldPanel("content_stream"),
                ],
                heading="Rédaction",
            ),
            ObjectList(
                [
                    FieldPanel("category"),
                    FieldPanel("tags"),
                    FieldPanel("featured"),
                    FieldPanel("youtube_url"),
                    FieldPanel("sources"),
                ],
                heading="Classement & sources",
            ),
            ObjectList(
                [
                    FieldPanel("slug"),
                    FieldPanel("published_at"),
                    PublishingPanel(),
                ],
                heading="Publication",
            ),
        ]
    )


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


# --- Tableau de bord : statistiques de lecture ----------------------------------


class ReadingStatsPanel(Component):
    name = "logos_reading_stats"
    order = 50
    template_name = "wagtailadmin/home/logos_stats_panel.html"

    def get_context_data(self, parent_context=None):
        now = timezone.now()
        last7 = now - timedelta(days=7)
        last30 = now - timedelta(days=30)
        top = (
            Article.objects.published()
            .annotate(
                v7=Count("views", filter=Q(views__created_at__gte=last7)),
                v30=Count("views", filter=Q(views__created_at__gte=last30)),
            )
            .order_by("-view_count")[:8]
        )
        days = []
        for i in range(13, -1, -1):
            day = (now - timedelta(days=i)).date()
            days.append({"day": day, "count": 0})
        counts = (
            ArticleView.objects.filter(created_at__date__gte=days[0]["day"])
            .values_list("created_at__date")
            .annotate(c=Count("id"))
        )
        by_day = {d: c for d, c in counts}
        peak = 1
        for d in days:
            d["count"] = by_day.get(d["day"], 0)
            peak = max(peak, d["count"])
        for d in days:
            d["pct"] = round(d["count"] * 100 / peak)
        total = sum(a.view_count for a in Article.objects.published())
        return {
            "top_articles": top,
            "days": days,
            "views_7": ArticleView.objects.filter(created_at__gte=last7).count(),
            "views_30": ArticleView.objects.filter(created_at__gte=last30).count(),
            "views_total": total,
            "drafts": Article.objects.filter(Q(live=False) | Q(has_unpublished_changes=True)).count(),
        }


@hooks.register("construct_homepage_panels")
def add_reading_stats(request, panels):
    panels.insert(0, ReadingStatsPanel())


@hooks.register("insert_global_admin_css")
def logos_admin_css():
    return format_html('<link rel="stylesheet" href="{}?v=20261002">', static("css/cms-editor.css"))
