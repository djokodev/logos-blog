from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, Category


class ArticleViewCountTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Theologie")
        self.article = Article.objects.create(
            title="Article test",
            excerpt="Resume test",
            category=self.category,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.detail_url = reverse("article_detail", kwargs={"slug": self.article.slug})

    def test_first_public_visit_increments_and_sets_cookie(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, 1)

        cookie_key = f"article_viewed_{self.article.pk}"
        self.assertIn(cookie_key, response.cookies)
        self.assertEqual(response.cookies[cookie_key].value, "1")

    def test_repeated_visit_with_same_client_does_not_increment_within_24h(self):
        self.client.get(self.detail_url)
        self.client.get(self.detail_url)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, 1)

    def test_second_client_counts_as_new_view(self):
        self.client.get(self.detail_url)
        other_client = self.client_class()
        other_client.get(self.detail_url)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, 2)

    def test_preview_does_not_increment_view_count(self):
        User = get_user_model()
        staff_user = User.objects.create_user(
            username="staff",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        preview_url = reverse("article_preview", kwargs={"pk": self.article.pk})
        response = self.client.get(preview_url)
        self.assertEqual(response.status_code, 200)

        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, 0)
