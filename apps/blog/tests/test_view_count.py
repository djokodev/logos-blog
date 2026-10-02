from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, ArticleView, Category
from blog.tracking import VISITOR_COOKIE

BROWSER_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"


class ArticleViewCountTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Théologie")
        self.article = Article.objects.create(
            title="Article test",
            excerpt="Résumé test",
            category=self.category,
            live=True,
            published_at=timezone.now() - timedelta(hours=1),
        )
        self.detail_url = reverse("article_detail", kwargs={"slug": self.article.slug})
        self.beacon_url = reverse("article_view_beacon", kwargs={"pk": self.article.pk})

    def _beacon(self, client=None, ip="41.202.1.10", ua=BROWSER_UA):
        client = client or self.client
        return client.post(self.beacon_url, HTTP_USER_AGENT=ua, HTTP_CF_CONNECTING_IP=ip)

    def _count(self):
        self.article.refresh_from_db()
        return self.article.view_count

    def test_page_display_alone_does_not_count(self):
        self.assertEqual(self.client.get(self.detail_url, HTTP_USER_AGENT=BROWSER_UA).status_code, 200)
        self.assertEqual(self._count(), 0)

    def test_first_beacon_counts_and_sets_visitor_cookie(self):
        response = self._beacon()
        self.assertEqual(response.json(), {"counted": True})
        self.assertIn(VISITOR_COOKIE, response.cookies)
        self.assertEqual(self._count(), 1)

    def test_same_visitor_never_counted_twice(self):
        self._beacon()
        self._beacon(ip="41.202.9.99")  # même cookie, autre réseau (ex. passage wifi -> 4G)
        self._beacon()
        self.assertEqual(self._count(), 1)

    def test_cookie_cleared_same_device_within_24h_not_recounted(self):
        self._beacon()
        other = self.client_class()  # pas de cookie
        self.assertEqual(self._beacon(client=other).json(), {"counted": False})
        self.assertEqual(self._count(), 1)

    def test_two_different_people_count_twice(self):
        self._beacon()
        other = self.client_class()
        self._beacon(client=other, ip="102.244.5.6")
        self.assertEqual(self._count(), 2)

    def test_bots_and_link_previews_ignored(self):
        for ua in ["WhatsApp/2.23.20.0", "facebookexternalhit/1.1", "Googlebot/2.1", "curl/8.0", ""]:
            self._beacon(client=self.client_class(), ua=ua, ip="1.1.1.1")
        self.assertEqual(self._count(), 0)

    def test_staff_not_counted(self):
        user = get_user_model().objects.create_user(username="staff", password="x-pass-123", is_staff=True)
        self.client.force_login(user)
        self._beacon()
        self.assertEqual(self._count(), 0)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.beacon_url).status_code, 405)

    def test_unpublished_article_not_counted(self):
        self.article.live = False
        self.article.save()
        self._beacon()
        self.assertEqual(self._count(), 0)
        self.assertEqual(ArticleView.objects.count(), 0)

    def test_preview_does_not_count(self):
        staff = get_user_model().objects.create_user(username="ed", password="x-pass-123", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse("article_preview", kwargs={"pk": self.article.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._count(), 0)


class PublishingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Histoire")

    def test_draft_not_public(self):
        a = Article.objects.create(title="Brouillon", excerpt="x", category=self.category, live=False)
        self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 404)

    def test_publish_sets_date(self):
        a = Article.objects.create(title="Publié", excerpt="x", category=self.category, live=True)
        self.assertIsNotNone(a.published_at)
        self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 200)

    def test_pages_render(self):
        Article.objects.create(title="Un article", excerpt="Résumé", category=self.category, live=True)
        for url in ["/", "/articles/", "/a-propos/", "/articles/feed/", "/sitemap.xml", "/robots.txt",
                    f"/articles/categorie/{self.category.slug}/", "/articles/?q=article"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
