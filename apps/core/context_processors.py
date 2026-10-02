from django.conf import settings
from django.db.models import Count, Q

from blog.models import Category

WHATSAPP_GROUP_URL = "https://chat.whatsapp.com/CcFiBPW2ofjLqOrgGKWK29?mode=gi_t"


def global_context(request):
    """Variables globales injectées dans tous les gabarits."""
    try:
        categories = list(
            Category.objects.annotate(n=Count("articles", filter=Q(articles__live=True)))
            .filter(n__gt=0)
            .order_by("-n", "name")
        )
    except Exception:
        categories = []

    base_url = settings.SITE_URL or f"{request.scheme}://{request.get_host()}"
    return {
        "SITE_NAME": "LOGOS",
        "SITE_TAGLINE": "Examiner la foi, chercher la vérité",
        "SITE_DESCRIPTION": (
            "Carnet de recherche sur les grandes questions spirituelles : histoire des religions, "
            "Bible, foi et raison, explorées avec honnêteté et rigueur."
        ),
        "SITE_URL": settings.SITE_URL,
        "BASE_URL": base_url,
        "ASSET_VERSION": getattr(settings, "ASSET_VERSION", "1"),
        "YOUTUBE_URL": "https://www.youtube.com/@logos_fr",
        "WHATSAPP_GROUP_URL": WHATSAPP_GROUP_URL,
        "GLOBAL_CATEGORIES": categories,
    }
