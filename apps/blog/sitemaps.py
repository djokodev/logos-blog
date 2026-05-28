from django.contrib.sitemaps import Sitemap

from .models import Article


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Article.objects.published()

    def lastmod(self, obj):
        return obj.updated_at
