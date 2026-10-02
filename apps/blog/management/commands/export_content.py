"""Export portable du contenu éditorial de LOGOS (indépendant de la version de PostgreSQL).

Usage :
    python manage.py export_content > logos-content.json
    python manage.py export_content --output /chemin/logos-content.json

Le fichier contient catégories, tags, images (métadonnées + chemin du fichier),
articles (contenu complet, statut, dates, vues) et les vues uniques.
Les fichiers images eux-mêmes sont dans l'archive media (media.tar.gz).
Réimport : python manage.py import_content logos-content.json
"""
import json
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.images import get_image_model

from blog.models import Article, ArticleView, Category, Tag

FORMAT_VERSION = 1


def _dt(value):
    return value.isoformat() if value else None


class Command(BaseCommand):
    help = "Exporte tout le contenu éditorial en JSON (sauvegarde portable)."

    def add_arguments(self, parser):
        parser.add_argument("--output", "-o", help="Fichier de sortie (par défaut : sortie standard)")

    def handle(self, *args, **opts):
        Image = get_image_model()
        data = {
            "format": "logos-content",
            "version": FORMAT_VERSION,
            "exported_at": timezone.now().isoformat(),
            "categories": [
                {"id": c.pk, "name": c.name, "slug": c.slug, "description": c.description}
                for c in Category.objects.order_by("pk")
            ],
            "tags": [{"id": t.pk, "name": t.name, "slug": t.slug} for t in Tag.objects.order_by("pk")],
            "images": [
                {
                    "id": i.pk,
                    "title": i.title,
                    "file": i.file.name,
                    "width": i.width,
                    "height": i.height,
                    "focal_point_x": i.focal_point_x,
                    "focal_point_y": i.focal_point_y,
                    "focal_point_width": i.focal_point_width,
                    "focal_point_height": i.focal_point_height,
                    "description": getattr(i, "description", ""),
                }
                for i in Image.objects.order_by("pk")
            ],
            "articles": [],
            "views": [
                {"article": v.article_id, "visitor": v.visitor, "fingerprint": v.fingerprint, "created_at": _dt(v.created_at)}
                for v in ArticleView.objects.order_by("pk")
            ],
        }
        for a in Article.objects.order_by("pk").prefetch_related("tags"):
            data["articles"].append(
                {
                    "id": a.pk,
                    "title": a.title,
                    "slug": a.slug,
                    "excerpt": a.excerpt,
                    "category": a.category_id,
                    "tags": [t.pk for t in a.tags.all()],
                    "cover": a.cover_id,
                    "cover_image_legacy": a.cover_image.name if a.cover_image else "",
                    "youtube_url": a.youtube_url,
                    "content_legacy": a.content,
                    "content_stream": list(a.content_stream.raw_data) if a.content_stream else [],
                    "sources": a.sources,
                    "featured": a.featured,
                    "live": a.live,
                    "view_count": a.view_count,
                    "published_at": _dt(a.published_at),
                    "first_published_at": _dt(a.first_published_at),
                    "created_at": _dt(a.created_at),
                    "updated_at": _dt(a.updated_at),
                }
            )

        payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if opts.get("output"):
            with open(opts["output"], "w", encoding="utf-8") as fh:
                fh.write(payload)
            self.stderr.write(self.style.SUCCESS(f"{len(data['articles'])} article(s) exporté(s) -> {opts['output']}"))
        else:
            sys.stdout.write(payload)
