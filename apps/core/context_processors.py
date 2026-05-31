from django.conf import settings

from blog.models import Category

def global_context(request):
    """
    Context processor to inject global LOGOS parameters into all templates.
    """
    try:
        # Load all categories for use in navigation menus
        categories = Category.objects.all().order_by('name')
    except Exception:
        categories = []

    return {
        'SITE_NAME': 'LOGOS',
        'SITE_TAGLINE': 'Questions personnelles. Recherche rigoureuse. Partage.',
        'SITE_URL': settings.SITE_URL,
        'YOUTUBE_URL': 'https://www.youtube.com/@logos_fr',
        'WHATSAPP_URL': 'https://wa.me/33600000000', # Placeholder WhatsApp link, can be customized
        'GLOBAL_CATEGORIES': categories,
    }
