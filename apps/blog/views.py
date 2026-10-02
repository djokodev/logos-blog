from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Article, Category
from .tracking import VISITOR_COOKIE, VISITOR_COOKIE_MAX_AGE, get_or_create_visitor_id, register_view

PER_PAGE = 9


def _published():
    return Article.objects.published().select_related("category", "cover").prefetch_related("tags")


def article_list(request):
    categories = Category.objects.filter(articles__live=True).distinct()
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    current_category = None
    articles = _published()
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        articles = articles.filter(category=current_category)

    if query:
        try:
            ids = [a.pk for a in articles.search(query, operator="or")]
        except Exception:
            ids = list(articles.filter(title__icontains=query).values_list("pk", flat=True))
        preserved = {pk: i for i, pk in enumerate(ids)}
        results = sorted(articles.filter(pk__in=ids), key=lambda a: preserved.get(a.pk, 0))
        page_obj = Paginator(results, PER_PAGE).get_page(request.GET.get("page"))
    else:
        page_obj = Paginator(articles, PER_PAGE).get_page(request.GET.get("page"))

    return render(
        request,
        "blog/article_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "categories": categories,
            "current_category": current_category,
        },
    )


def article_detail(request, slug):
    article = get_object_or_404(_published(), slug=slug)
    return render(
        request,
        "blog/article_detail.html",
        {
            "article": article,
            "related_articles": article.get_related_articles(),
            "previous_article": article.get_previous_article(),
            "next_article": article.get_next_article(),
        },
    )


@require_POST
def article_view_beacon(request, pk):
    """Appelée par le navigateur après quelques secondes de lecture."""
    article = get_object_or_404(Article, pk=pk)
    visitor_id, is_new = get_or_create_visitor_id(request)
    counted = register_view(request, article, visitor_id)
    response = JsonResponse({"counted": counted})
    if is_new:
        response.set_cookie(
            VISITOR_COOKIE,
            visitor_id,
            max_age=VISITOR_COOKIE_MAX_AGE,
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
        )
    response["Cache-Control"] = "no-store"
    return response


@staff_member_required(login_url="/cms/login/")
def article_preview(request, pk):
    article = get_object_or_404(Article.objects.select_related("category"), pk=pk)
    return render(
        request,
        "blog/article_detail.html",
        {
            "article": article,
            "related_articles": article.get_related_articles(),
            "preview_mode": True,
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = _published().filter(category=category)
    page_obj = Paginator(articles, PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "blog/category_detail.html", {"category": category, "page_obj": page_obj})
