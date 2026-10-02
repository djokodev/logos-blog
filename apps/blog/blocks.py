"""Blocs éditoriaux de LOGOS (StreamField).

Les anciens types de blocs (heading, paragraph, image, image_text, quote, video)
sont conservés à l'identique pour rester compatibles avec les articles existants.
"""
from wagtail import blocks
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageBlock, ImageChooserBlock

RICH_FEATURES = [
    "h2", "h3", "h4",
    "bold", "italic", "strikethrough", "superscript",
    "link", "document-link",
    "ol", "ul", "blockquote", "hr", "code",
    "image", "embed",
]

SHORT_RICH_FEATURES = ["bold", "italic", "link", "ol", "ul", "superscript"]


class CalloutBlock(blocks.StructBlock):
    kind = blocks.ChoiceBlock(
        choices=[
            ("note", "Note"),
            ("reflexion", "Pour réfléchir"),
            ("definition", "Définition"),
            ("attention", "Attention / nuance"),
            ("retenir", "À retenir"),
        ],
        default="note",
        label="Type d'encadré",
    )
    title = blocks.CharBlock(required=False, label="Titre (optionnel)")
    text = blocks.RichTextBlock(features=SHORT_RICH_FEATURES, label="Contenu")

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        context["kind_label"] = dict(self.child_blocks["kind"].field.choices).get(value.get("kind"), "Note")
        return context

    class Meta:
        icon = "help"
        label = "Encadré (note, définition, à retenir…)"
        template = "blog/blocks/callout_block.html"


class BibleVerseBlock(blocks.StructBlock):
    text = blocks.TextBlock(label="Texte du verset", rows=3)
    reference = blocks.CharBlock(label="Référence", help_text="Ex. : Proverbes 3:21-22")
    version = blocks.CharBlock(
        required=False,
        default="Louis Segond 1910",
        label="Version",
    )

    class Meta:
        icon = "openquote"
        label = "Verset biblique"
        template = "blog/blocks/verse_block.html"


class TimelineEventBlock(blocks.StructBlock):
    date = blocks.CharBlock(label="Date / période", help_text="Ex. : 325, 1054, XVIe siècle")
    title = blocks.CharBlock(label="Événement")
    text = blocks.TextBlock(required=False, rows=2, label="Description courte")


class TimelineBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, label="Titre de la chronologie")
    events = blocks.ListBlock(TimelineEventBlock(), label="Événements", min_num=1)

    class Meta:
        icon = "date"
        label = "Chronologie"
        template = "blog/blocks/timeline_block.html"


class KeyPointsBlock(blocks.StructBlock):
    title = blocks.CharBlock(default="En résumé", label="Titre")
    points = blocks.ListBlock(blocks.CharBlock(label="Point"), label="Points clés", min_num=1)

    class Meta:
        icon = "list-ul"
        label = "Points clés / résumé"
        template = "blog/blocks/keypoints_block.html"


class FigureBlock(blocks.StructBlock):
    image = ImageChooserBlock(label="Image")
    caption = blocks.CharBlock(required=False, label="Légende")
    credit = blocks.CharBlock(required=False, label="Crédit / source")
    width = blocks.ChoiceBlock(
        choices=[("text", "Largeur du texte"), ("wide", "Large"), ("small", "Petite")],
        default="text",
        label="Largeur",
    )

    class Meta:
        icon = "image"
        label = "Image avec légende"
        template = "blog/blocks/figure_block.html"


def article_stream_blocks():
    return [
        # --- Blocs principaux -------------------------------------------------
        (
            "paragraph",
            blocks.RichTextBlock(
                features=RICH_FEATURES,
                icon="pilcrow",
                label="Texte",
            ),
        ),
        ("figure", FigureBlock()),
        ("verse", BibleVerseBlock()),
        ("callout", CalloutBlock()),
        ("timeline", TimelineBlock()),
        ("key_points", KeyPointsBlock()),
        (
            "image_text",
            blocks.StructBlock(
                [
                    ("text", blocks.RichTextBlock(features=["bold", "italic", "link", "ol", "ul", "blockquote"])),
                    ("image", ImageChooserBlock(required=False)),
                    (
                        "image_position",
                        blocks.ChoiceBlock(
                            choices=[("right", "Image à droite"), ("left", "Image à gauche")],
                            default="right",
                            required=True,
                        ),
                    ),
                    (
                        "image_size",
                        blocks.ChoiceBlock(
                            choices=[("sm", "Petite"), ("md", "Moyenne"), ("lg", "Grande")],
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
        # --- Anciens blocs (compatibilité) --------------------------------------
        (
            "heading",
            blocks.CharBlock(
                form_classname="title",
                icon="title",
                label="Titre de section (ancien bloc)",
                template="blog/blocks/heading_block.html",
            ),
        ),
        ("image", ImageBlock(label="Image simple (ancien bloc)")),
    ]
