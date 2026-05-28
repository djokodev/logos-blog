from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from .models import Article, Category


def article_list(request):
    articles = Article.objects.published().select_related("category").prefetch_related("tags")
    categories = Category.objects.all()

    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query))

    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        articles = articles.filter(category=current_category)

    paginator = Paginator(articles, 3)
    page_obj = paginator.get_page(request.GET.get("page"))

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
    article = get_object_or_404(
        Article.objects.published().select_related("category").prefetch_related("tags"),
        slug=slug,
    )
    view_cookie_name = f"article_viewed_{article.pk}"
    should_increment = not request.COOKIES.get(view_cookie_name)

    if should_increment:
        Article.objects.filter(pk=article.pk).update(view_count=F("view_count") + 1)
        article.view_count += 1

    related_articles = (
        Article.objects.published()
        .filter(category=article.category)
        .exclude(pk=article.pk)[:3]
    )

    response = render(
        request,
        "blog/article_detail.html",
        {
            "article": article,
            "related_articles": related_articles,
        },
    )
    if should_increment:
        response.set_cookie(
            view_cookie_name,
            "1",
            max_age=86400,
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
        )
    return response


@staff_member_required(login_url="/cms/login/")
def article_preview(request, pk):
    article = get_object_or_404(
        Article.objects.select_related("category").prefetch_related("tags"),
        pk=pk,
    )
    related_articles = (
        Article.objects.published()
        .filter(category=article.category)
        .exclude(pk=article.pk)[:3]
    )

    return render(
        request,
        "blog/article_detail.html",
        {
            "article": article,
            "related_articles": related_articles,
            "preview_mode": True,
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = Article.objects.published().filter(category=category).select_related("category")

    paginator = Paginator(articles, 3)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "blog/category_detail.html",
        {"category": category, "page_obj": page_obj},
    )
