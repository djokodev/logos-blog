"""Comptage de vues uniques par article.

Règles :
- Une vue n'est comptée qu'après que le lecteur est resté quelques secondes
  sur la page (balise JavaScript) : les robots, les prévisualisations de liens
  (WhatsApp, Facebook…) et les préchargements ne sont pas comptés.
- Un même visiteur n'est compté qu'UNE fois par article, pour toujours :
  il est reconnu par un identifiant anonyme stocké dans un cookie (2 ans).
- Si le cookie est bloqué ou effacé, une empreinte anonyme (IP + navigateur,
  hachée et salée) évite de recompter le même appareil pendant 24 h.
- Les administrateurs connectés ne sont jamais comptés.
- Aucune donnée personnelle en clair n'est stockée (uniquement des hachages).
"""
import hashlib
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import Article, ArticleView

VISITOR_COOKIE = "logos_vid"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2
FINGERPRINT_WINDOW = timedelta(hours=24)

BOT_UA = re.compile(
    r"bot|crawl|spider|slurp|preview|facebookexternalhit|whatsapp|telegram|discord|"
    r"headless|lighthouse|pingdom|uptime|monitor|curl|wget|python|httpx|java/|go-http|"
    r"axios|node-fetch|scrapy|semrush|ahrefs|bingpreview|embedly|quora link",
    re.IGNORECASE,
)


def _hash(*parts):
    raw = "|".join([settings.SECRET_KEY, *parts])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def client_ip(request):
    for header in ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP"):
        value = request.META.get(header)
        if value:
            return value.strip()
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_bot(request):
    ua = request.META.get("HTTP_USER_AGENT", "")
    return not ua or bool(BOT_UA.search(ua))


def get_or_create_visitor_id(request):
    """Retourne (visitor_id, is_new)."""
    vid = request.COOKIES.get(VISITOR_COOKIE, "")
    if re.fullmatch(r"[A-Za-z0-9_-]{16,64}", vid or ""):
        return vid, False
    return secrets.token_urlsafe(18), True


def register_view(request, article: Article, visitor_id: str) -> bool:
    """Enregistre la vue si elle est nouvelle. Retourne True si comptée."""
    if request.user.is_authenticated and request.user.is_staff:
        return False
    if is_bot(request) or not article.is_published:
        return False

    visitor = _hash("v", visitor_id)
    fingerprint = _hash("f", client_ip(request), request.META.get("HTTP_USER_AGENT", ""))

    seen = ArticleView.objects.filter(article=article, visitor=visitor).exists() or ArticleView.objects.filter(
        article=article,
        fingerprint=fingerprint,
        created_at__gte=timezone.now() - FINGERPRINT_WINDOW,
    ).exists()
    if seen:
        return False

    try:
        with transaction.atomic():
            ArticleView.objects.create(article=article, visitor=visitor, fingerprint=fingerprint)
            Article.objects.filter(pk=article.pk).update(view_count=F("view_count") + 1)
    except IntegrityError:
        return False
    return True
