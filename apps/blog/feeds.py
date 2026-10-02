from django.conf import settings
from django.contrib.syndication.views import Feed

from .models import Article


class LatestArticlesFeed(Feed):
    title = "LOGOS — Examiner la foi, chercher la vérité"
    link = "/articles/"
    description = "Les derniers articles publiés sur LOGOS."

    def items(self):
        return Article.objects.published().select_related("category")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_categories(self, item):
        return [item.category.name]
