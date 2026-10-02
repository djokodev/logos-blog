"""Réimporte un export JSON de LOGOS (voir export_content).

Usage :
    python manage.py import_content logos-content.json [--dry-run]

- Idempotent : les articles sont rapprochés par leur slug (mis à jour s'ils existent).
- Les images gardent leur identifiant d'origine quand c'est possible, pour que les
  références dans le contenu restent valides. Restaurez d'abord les fichiers media
  (media.tar.gz) pour que les images s'affichent.
- Les compteurs de vues ne sont jamais diminués.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils.dateparse import parse_datetime
from wagtail.images import get_image_model
from wagtail.models import Collection

from blog.models import Article, ArticleView, Category, Tag


def _dt(value):
    return parse_datetime(value) if value else None


class Command(BaseCommand):
    help = "Importe un export JSON de contenu LOGOS."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true", help="Simule sans rien enregistrer")

    def handle(self, path, dry_run=False, **opts):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("format") != "logos-content":
            raise CommandError("Ce fichier n'est pas un export LOGOS.")

        Image = get_image_model()
        root = Collection.get_first_root_node()
        stats = {"categories": 0, "tags": 0, "images": 0, "articles_created": 0, "articles_updated": 0, "views": 0}

        with transaction.atomic():
            cat_map, tag_map = {}, {}
            for c in data["categories"]:
                obj, created = Category.objects.get_or_create(slug=c["slug"], defaults={"name": c["name"], "description": c["description"]})
                cat_map[c["id"]] = obj
                stats["categories"] += int(created)
            for t in data["tags"]:
                obj, created = Tag.objects.get_or_create(slug=t["slug"], defaults={"name": t["name"]})
                tag_map[t["id"]] = obj
                stats["tags"] += int(created)

            for i in data["images"]:
                existing = Image.objects.filter(pk=i["id"]).first()
                if existing:
                    if existing.file.name != i["file"]:
                        self.stderr.write(self.style.WARNING(f"Image #{i['id']} déjà utilisée par un autre fichier, ignorée."))
                    continue
                Image.objects.create(
                    pk=i["id"], title=i["title"], file=i["file"], width=i["width"], height=i["height"],
                    focal_point_x=i["focal_point_x"], focal_point_y=i["focal_point_y"],
                    focal_point_width=i["focal_point_width"], focal_point_height=i["focal_point_height"],
                    collection=root,
                )
                stats["images"] += 1

            art_map = {}
            for a in data["articles"]:
                article = Article.objects.filter(slug=a["slug"]).first()
                created = article is None
                article = article or Article(slug=a["slug"])
                article.title = a["title"]
                article.excerpt = a["excerpt"]
                article.category = cat_map[a["category"]]
                article.cover_id = a["cover"] if a["cover"] and Image.objects.filter(pk=a["cover"]).exists() else None
                if a.get("cover_image_legacy"):
                    article.cover_image.name = a["cover_image_legacy"]
                article.youtube_url = a["youtube_url"]
                article.content = a.get("content_legacy", "")
                article.content_stream = a["content_stream"]
                article.sources = a["sources"]
                article.featured = a["featured"]
                article.live = a["live"]
                article.published_at = _dt(a["published_at"])
                article.first_published_at = _dt(a.get("first_published_at"))
                article.view_count = max(article.view_count or 0, a["view_count"])
                article.save()
                article.tags.set([tag_map[t] for t in a["tags"] if t in tag_map])
                art_map[a["id"]] = article
                stats["articles_created" if created else "articles_updated"] += 1

            for v in data.get("views", []):
                art = art_map.get(v["article"])
                if art and not ArticleView.objects.filter(article=art, visitor=v["visitor"]).exists():
                    ArticleView.objects.create(article=art, visitor=v["visitor"], fingerprint=v["fingerprint"], created_at=_dt(v["created_at"]))
                    stats["views"] += 1

            # Les images ont été créées avec un identifiant explicite : on recale la séquence.
            with connection.cursor() as cursor:
                for sql in connection.ops.sequence_reset_sql(no_style(), [Image]):
                    cursor.execute(sql)

            if dry_run:
                transaction.set_rollback(True)

        prefix = "[SIMULATION] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(prefix + ", ".join(f"{k}: {v}" for k, v in stats.items())))
