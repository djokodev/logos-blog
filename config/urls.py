from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from blog.sitemaps import ArticleSitemap

sitemaps = {
    "articles": ArticleSitemap,
}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("cms/", include(wagtailadmin_urls)),
    path("cms/documents/", include(wagtaildocs_urls)),
    path("", include("core.urls")),
    path("articles/", include("blog.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", lambda request: HttpResponse("User-agent: *\nAllow: /\nSitemap: /sitemap.xml", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.custom_404"
