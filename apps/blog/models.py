from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from wagtail import blocks
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.blocks import ImageBlock
from wagtail.models import PreviewableMixin


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


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED, published_at__lte=timezone.now())


class Article(PreviewableMixin, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"
        ARCHIVED = "archived", "Archivé"

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    excerpt = models.TextField(help_text="Résumé court affiché dans les listes")
    cover_image = models.ImageField(upload_to="articles/covers/", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="articles")
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")
    youtube_url = models.URLField(blank=True)
    content = models.TextField(
        blank=True,
        default="",
        help_text="Optionnel (compatibilité). Préférez Content stream pour les nouveaux articles.",
    )
    content_stream = StreamField(
        [
            (
                "heading",
                blocks.CharBlock(
                    form_classname="title",
                    icon="title",
                    label="Titre de section (H2)",
                    template="blog/blocks/heading_block.html",
                ),
            ),
            (
                "paragraph",
                blocks.RichTextBlock(
                    features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "hr", "blockquote", "image", "embed"],
                    icon="pilcrow",
                    label="Paragraphe riche",
                ),
            ),
            ("image", ImageBlock(label="Image")),
            (
                "image_text",
                blocks.StructBlock(
                    [
                        ("text", blocks.RichTextBlock(features=["bold", "italic", "link", "ol", "ul", "blockquote"])),
                        ("image", ImageChooserBlock(required=False)),
                        (
                            "image_position",
                            blocks.ChoiceBlock(
                                choices=[
                                    ("right", "Image à droite"),
                                    ("left", "Image à gauche"),
                                ],
                                default="right",
                                required=True,
                            ),
                        ),
                        (
                            "image_size",
                            blocks.ChoiceBlock(
                                choices=[
                                    ("sm", "Petite"),
                                    ("md", "Moyenne"),
                                    ("lg", "Grande"),
                                ],
                                default="md",
                                required=True,
                                help_text="Taille visuelle de l'image dans la mise en page 2 colonnes.",
                            ),
                        ),
                    ],
                    icon="image",
                    label="Texte + image (2 colonnes)",
                    template="blog/blocks/image_text_block.html",
                ),
            ),
            ("quote", blocks.BlockQuoteBlock(icon="openquote", label="Citation")),
            ("video", EmbedBlock(icon="media", label="Vidéo (YouTube, Vimeo, etc.)")),
        ],
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Contenu éditorial riche via Wagtail (texte, images, vidéos intégrées).",
    )
    sources = models.TextField(blank=True, help_text="Sources, références, livres, liens")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(blank=True, null=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "published_at"]), models.Index(fields=["slug"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Article, self.title, self.pk)
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("article_detail", kwargs={"slug": self.slug})

    def get_preview_template(self, request, mode_name):
        return "blog/article_detail.html"

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        related_articles = []
        if self.category_id:
            related_articles = (
                Article.objects.published()
                .filter(category=self.category)
                .exclude(pk=self.pk)[:3]
            )
        context.update(
            {
                "article": self,
                "related_articles": related_articles,
                "preview_mode": True,
            }
        )
        return context

    @property
    def reading_time(self):
        words = len((self.content or "").split())
        if self.content_stream:
            for block in self.content_stream:
                value = block.value
                if isinstance(value, str):
                    words += len(value.split())
                elif hasattr(value, "source"):
                    words += len(str(value.source).split())
                elif isinstance(value, dict):
                    words += sum(len(str(v).split()) for v in value.values())
        minutes = max(1, round(words / 220))
        return minutes


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
