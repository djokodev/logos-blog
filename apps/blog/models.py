from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.html import strip_tags
from django.utils.text import slugify
from wagtail.fields import StreamField
from wagtail.models import DraftStateMixin, LockableMixin, PreviewableMixin, RevisionMixin
from wagtail.search import index
from wagtail.search.queryset import SearchableQuerySetMixin

from .blocks import article_stream_blocks


def _unique_slug(model_cls, source_value, instance_pk=None):
    base_slug = slugify(source_value) or "item"
    slug = base_slug
    suffix = 2
    qs = model_cls.objects.all()
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk)
        super().save(*args, **kwargs)


class Tag(TimestampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Tag, self.name, self.pk)
        super().save(*args, **kwargs)


class ArticleQuerySet(SearchableQuerySetMixin, models.QuerySet):
    def published(self):
        return self.filter(live=True, published_at__isnull=False, published_at__lte=timezone.now())


class Article(
    LockableMixin,
    DraftStateMixin,
    RevisionMixin,
    PreviewableMixin,
    index.Indexed,
    TimestampedModel,
):
    title = models.CharField("Titre", max_length=220)
    slug = models.SlugField(
        "Adresse (slug)",
        max_length=240,
        unique=True,
        blank=True,
        help_text="Généré automatiquement depuis le titre. Évitez de le changer après publication.",
    )
    excerpt = models.TextField(
        "Résumé",
        help_text="2 ou 3 phrases. Affiché dans les listes, sur Google et lors des partages WhatsApp.",
    )
    cover = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name="Image de couverture",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Idéalement au format paysage (au moins 1600 px de large).",
    )
    # Ancien champ (fichier brut) conservé comme repli pour les anciens articles.
    cover_image = models.ImageField(upload_to="articles/covers/", blank=True, null=True, editable=False)
    category = models.ForeignKey(Category, verbose_name="Catégorie", on_delete=models.PROTECT, related_name="articles")
    tags = models.ManyToManyField(Tag, verbose_name="Tags", blank=True, related_name="articles")
    youtube_url = models.URLField("Vidéo YouTube associée", blank=True)
    content = models.TextField(blank=True, default="", editable=False)
    content_stream = StreamField(
        article_stream_blocks(),
        use_json_field=True,
        blank=True,
        null=True,
        verbose_name="Contenu",
    )
    sources = models.TextField(
        "Sources et références",
        blank=True,
        help_text="Une source par ligne (les liens deviennent cliquables).",
    )
    featured = models.BooleanField("Mettre en avant sur l'accueil", default=False)
    view_count = models.PositiveIntegerField("Vues", default=0, editable=False)
    published_at = models.DateTimeField(
        "Date de publication affichée",
        blank=True,
        null=True,
        help_text="Remplie automatiquement à la première publication.",
    )

    _revisions = GenericRelation("wagtailcore.Revision", related_query_name="article")

    objects = ArticleQuerySet.as_manager()

    search_fields = [
        index.SearchField("title", boost=3),
        index.AutocompleteField("title"),
        index.SearchField("excerpt", boost=2),
        index.SearchField("content_stream"),
        index.SearchField("sources"),
        index.FilterField("live"),
        index.FilterField("published_at"),
        index.FilterField("category"),
    ]

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["live", "published_at"]), models.Index(fields=["slug"])]
        verbose_name = "article"
        verbose_name_plural = "articles"

    def __str__(self):
        return self.title

    @property
    def revisions(self):
        return self._revisions

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Article, self.title, self.pk)
        if self.live and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("article_detail", kwargs={"slug": self.slug})

    def get_url(self, request=None):
        return self.get_absolute_url()

    @property
    def is_published(self):
        return bool(self.live and self.published_at and self.published_at <= timezone.now())

    # --- Couverture -----------------------------------------------------------
    @property
    def has_cover(self):
        return bool(self.cover_id or self.cover_image)

    @property
    def legacy_cover_url(self):
        return self.cover_image.url if self.cover_image else ""

    # --- Navigation -----------------------------------------------------------
    def get_previous_article(self):
        if not self.published_at:
            return None
        return Article.objects.published().filter(published_at__lt=self.published_at).order_by("-published_at").first()

    def get_next_article(self):
        if not self.published_at:
            return None
        return Article.objects.published().filter(published_at__gt=self.published_at).order_by("published_at").first()

    def get_related_articles(self, limit=3):
        qs = Article.objects.published().exclude(pk=self.pk).select_related("category", "cover")
        same = list(qs.filter(category_id=self.category_id)[:limit])
        if len(same) < limit:
            same += list(qs.exclude(pk__in=[a.pk for a in same]).exclude(category_id=self.category_id)[: limit - len(same)])
        return same

    # --- Aperçu ---------------------------------------------------------------
    def get_preview_template(self, request, mode_name):
        return "blog/article_detail.html"

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        context.update(
            {
                "article": self,
                "related_articles": self.get_related_articles() if self.category_id else [],
                "preview_mode": True,
            }
        )
        return context

    @property
    def reading_time(self):
        words = 0
        if self.content_stream:
            for block in self.content_stream:
                words += len(strip_tags(" ".join(_block_text(block.value))).split())
        else:
            words = len((self.content or "").split())

        words_per_minute = max(120, int(getattr(settings, "READING_WORDS_PER_MINUTE", 400)))
        return max(1, round(words / words_per_minute))


def _block_text(value):
    """Extrait récursivement le texte d'une valeur de bloc."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if hasattr(value, "source"):
        return [str(value.source)]
    if isinstance(value, dict) or hasattr(value, "items"):
        out = []
        for v in value.values():
            out += _block_text(v)
        return out
    if isinstance(value, (list, tuple)) or hasattr(value, "__iter__") and not hasattr(value, "file"):
        out = []
        try:
            for v in value:
                out += _block_text(v)
        except TypeError:
            pass
        return out
    return []


class ArticleView(models.Model):
    """Une vue unique d'un article par un visiteur (dédupliquée)."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="views")
    visitor = models.CharField(max_length=64, db_index=True)
    fingerprint = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["article", "visitor"], name="unique_article_visitor")]
        verbose_name = "vue d'article"
        verbose_name_plural = "vues d'articles"


class Resource(TimestampedModel):
    class ResourceType(models.TextChoices):
        BOOK = "book", "Livre"
        VIDEO = "video", "Vidéo"
        ARTICLE = "article", "Article"
        WEBSITE = "website", "Site web"
        DOCUMENT = "document", "Document"
        OTHER = "other", "Autre"

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField()
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, default=ResourceType.OTHER)
    related_article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True, related_name="resources")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Resource, self.title, self.pk)
        super().save(*args, **kwargs)
