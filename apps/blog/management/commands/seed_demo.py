from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from blog.models import Article, Category, Resource, Tag


class Command(BaseCommand):
    help = "Crée des données de démonstration LOGOS"

    def handle(self, *args, **options):
        categories = [
            "Bible",
            "Histoire de l'Église",
            "Dénominations chrétiennes",
            "Théologie",
            "Questions spirituelles",
            "Foi & raison",
        ]
        cat_objs = {}
        for name in categories:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
            cat_objs[name] = cat

        tags = ["Exégèse", "Doctrine", "Histoire", "Apologétique", "Lecture biblique"]
        tag_objs = []
        for name in tags:
            tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
            tag_objs.append(tag)

        articles = [
            ("Pourquoi existe-t-il autant de dénominations chrétiennes ?", "Dénominations chrétiennes"),
            ("Qu'est-ce que l'Église primitive ?", "Histoire de l'Église"),
            ("Comment lire la Bible avec sérieux et honnêteté ?", "Bible"),
            ("Foi et raison sont-elles opposées ?", "Foi & raison"),
            ("Pourquoi les chrétiens ne sont-ils pas toujours d'accord entre eux ?", "Théologie"),
        ]

        for idx, (title, category_name) in enumerate(articles, start=1):
            article, created = Article.objects.get_or_create(
                slug=slugify(title),
                defaults={
                    "title": title,
                    "excerpt": "Une exploration claire, honnête et rigoureuse de cette question.",
                    "category": cat_objs[category_name],
                    "content": "## Introduction\n\nVoici une version de démonstration pour LOGOS.\n\n## Développement\n\n- Argument 1\n- Argument 2\n- Argument 3\n\n## Conclusion\n\nLa recherche biblique demande humilité et rigueur.",
                    "sources": "- Bible\n- Ouvrages d'histoire de l'Église\n- Notes de recherche personnelles",
                    "status": Article.Status.PUBLISHED,
                    "published_at": timezone.now() - timezone.timedelta(days=idx),
                    "featured": idx <= 2,
                },
            )
            if created:
                article.tags.set(tag_objs[:3])

        Resource.objects.get_or_create(
            slug="manuel-introduction-theologie",
            defaults={
                "title": "Manuel d'introduction à la théologie",
                "description": "Une base utile pour commencer un parcours de théologie.",
                "url": "https://example.com/theologie",
                "resource_type": Resource.ResourceType.BOOK,
            },
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées ou déjà présentes."))
