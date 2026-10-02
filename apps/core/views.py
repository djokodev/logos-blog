from django.shortcuts import render
from django.views.generic import TemplateView

from blog.models import Article, Category


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = Article.objects.published().select_related("category", "cover")
        featured = published.filter(featured=True).first() or published.first()
        context["featured_article"] = featured
        context["other_articles"] = list(published.exclude(pk=featured.pk)[:6]) if featured else []
        return context


class AboutView(TemplateView):
    template_name = "pages/about.html"


def contact_view(request):
    return render(request, "pages/contact.html")


def custom_404(request, exception):
    return render(request, "pages/404.html", status=404)
