from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0005_alter_article_content_stream"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="view_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
