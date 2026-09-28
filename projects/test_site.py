"""Permissions, edge cases, and a smoke test of every page in English and Arabic."""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from main.models import Profile

from .models import Category, Comment, Donation, Project, ProjectReport, Rating

TEMP_MEDIA = tempfile.mkdtemp()
PASSWORD = 'StrongPass#1'


def make_project(owner, **fields):
    now = timezone.now()
    values = dict(
        owner=owner, title='Library books', details='Books', category=Category.objects.get(name='Education'),
        total_target=Decimal('1000'), start_time=now - timedelta(days=1), end_time=now + timedelta(days=10),
    )
    values.update(fields)
    return Project.objects.create(**values)


class AccessControlTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner@x.com', 'owner@x.com', PASSWORD)
        self.other = User.objects.create_user('other@x.com', 'other@x.com', PASSWORD)
        self.project = make_project(self.owner)
        self.comment = Comment.objects.create(project=self.project, user=self.owner, content='hi')

    def test_anonymous_users_are_sent_to_login(self):
        pk = self.project.pk
        get_pages = ['project_create', 'my_projects', 'my_donations', 'profile', 'dashboard', 'logout']
        post_pages = [('donate', pk), ('add_comment', pk), ('rate_project', pk), ('report_project', pk),
                      ('cancel_project', pk), ('report_comment', self.comment.pk), ('delete_account', None)]
        for name in get_pages:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response['Location'].startswith(reverse('auth_page')), name)
        for name, arg in post_pages:
            url = reverse(name, args=[arg] if arg else [])
            response = self.client.post(url, {'amount': 10, 'content': 'x', 'value': 5, 'reason': 'x', 'password': 'x'})
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response['Location'].startswith(reverse('auth_page')), name)
        self.assertEqual(Donation.objects.count() + Rating.objects.count() + ProjectReport.objects.count(), 0)

    def test_actions_only_accept_post(self):
        self.client.force_login(self.other)
        for name in ['donate', 'add_comment', 'rate_project', 'report_project', 'cancel_project']:
            self.assertEqual(self.client.get(reverse(name, args=[self.project.pk])).status_code, 405, name)

    def test_missing_objects_give_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('project_detail', args=[99999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('category_projects', args=[99999])).status_code, 404)
        self.assertEqual(self.client.post(reverse('donate', args=[99999]), {'amount': 5}).status_code, 404)

    def test_reply_to_a_comment_from_another_project_is_rejected(self):
        other_project = make_project(self.other, title='Other')
        self.client.force_login(self.other)
        response = self.client.post(reverse('add_comment', args=[other_project.pk]), {'content': 'x', 'parent_id': self.comment.pk})
        self.assertEqual(response.status_code, 404)


class EdgeCaseTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner@x.com', 'owner@x.com', PASSWORD)
        self.donor = User.objects.create_user('donor@x.com', 'donor@x.com', PASSWORD)
        self.project = make_project(self.owner)
        self.client.force_login(self.donor)

    def donate(self, amount, project=None):
        return self.client.post(reverse('donate', args=[(project or self.project).pk]), {'amount': amount})

    def test_invalid_donation_amounts_are_rejected(self):
        for amount in ['0', '-50', 'abc', '', '0.5', '99999999999999']:
            self.donate(amount)
        self.assertEqual(Donation.objects.count(), 0)

    def test_no_donations_before_start_or_after_end(self):
        now = timezone.now()
        future = make_project(self.owner, title='Future', start_time=now + timedelta(days=2), end_time=now + timedelta(days=5))
        ended = make_project(self.owner, title='Ended', start_time=now - timedelta(days=5), end_time=now - timedelta(days=1))
        self.donate(100, future)
        self.donate(100, ended)
        self.assertEqual(Donation.objects.count(), 0)

    def test_ratings_outside_1_to_5_are_rejected(self):
        for value in ['0', '6', '-1', 'five', '']:
            self.client.post(reverse('rate_project', args=[self.project.pk]), {'value': value})
        self.assertEqual(Rating.objects.count(), 0)

    def test_report_project_and_comment(self):
        from .models import CommentReport
        comment = Comment.objects.create(project=self.project, user=self.owner, content='rude')
        response = self.client.post(reverse('report_project', args=[self.project.pk]), {'reason': 'Looks like a scam'}, follow=True)
        self.assertContains(response, 'Report submitted')
        response = self.client.post(reverse('report_comment', args=[comment.pk]), {'reason': 'Offensive'}, follow=True)
        self.assertRedirects(response, reverse('project_detail', args=[self.project.pk]))
        self.assertContains(response, 'Comment reported')
        report = ProjectReport.objects.get()
        self.assertEqual((report.user, report.reason), (self.donor, 'Looks like a scam'))
        self.assertEqual(CommentReport.objects.get().comment, comment)

    def test_empty_comment_and_report_are_ignored(self):
        self.client.post(reverse('add_comment', args=[self.project.pk]), {'content': ''})
        self.client.post(reverse('report_project', args=[self.project.pk]), {'reason': ''})
        self.assertEqual(Comment.objects.count() + ProjectReport.objects.count(), 0)

    def test_cancelled_campaign_hidden_from_home_and_search_but_page_still_opens(self):
        self.project.is_cancelled = True
        self.project.save()
        self.assertNotContains(self.client.get(reverse('home')), 'Library books')
        self.assertNotContains(self.client.get(reverse('search'), {'q': 'Library'}), 'Library books')
        self.assertContains(self.client.get(reverse('project_detail', args=[self.project.pk])), 'cancelled by its owner')

    def test_home_shows_top_5_rated_latest_5_featured_5(self):
        projects = [make_project(self.owner, title=f'Campaign {i}', is_featured=True) for i in range(7)]
        for i, p in enumerate(projects):
            Rating.objects.create(project=p, user=self.donor, value=1 + i % 5)
        context = self.client.get(reverse('home')).context
        self.assertEqual(len(context['top_rated']), 5)
        self.assertEqual(len(context['latest']), 5)
        self.assertEqual(len(context['featured']), 5)
        ratings = [p.avg_rating for p in context['top_rated']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))

    def test_similar_projects_share_tags_and_exclude_itself(self):
        self.project.tags.create(name='books')
        similar = make_project(self.owner, title='More books')
        similar.tags.add(self.project.tags.get())
        unrelated = make_project(self.owner, title='Unrelated')
        context = self.client.get(reverse('project_detail', args=[self.project.pk])).context
        self.assertEqual(list(context['similar']), [similar])
        self.assertNotIn(unrelated, context['similar'])

    def test_campaign_end_date_must_be_in_the_future(self):
        self.client.force_login(self.owner)
        now = timezone.localtime()
        response = self.client.post(reverse('project_create'), {
            'title': 'Past', 'details': 'x', 'category': self.project.category.pk, 'total_target': '100',
            'start_time': (now - timedelta(days=10)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertContains(response, 'End time must be in the future')
        self.assertFalse(Project.objects.filter(title='Past').exists())

    def test_campaign_needs_at_least_one_picture(self):
        self.client.force_login(self.owner)
        now = timezone.localtime()
        self.client.post(reverse('project_create'), {
            'title': 'No pics', 'details': 'x', 'category': self.project.category.pk, 'total_target': '100',
            'start_time': now.strftime('%Y-%m-%dT%H:%M'), 'end_time': (now + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertFalse(Project.objects.filter(title='No pics').exists())

    def test_deleting_a_user_removes_their_campaigns_and_donations(self):
        Donation.objects.create(project=self.project, user=self.donor, amount=10)
        self.owner.delete()
        self.assertFalse(Project.objects.exists())
        self.assertFalse(Donation.objects.exists())

    def test_category_with_campaigns_cannot_be_deleted(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.project.category.delete()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class WholeSiteSmokeTests(TestCase):
    """Open every page as a visitor, a donor, the owner and an admin, in English and Arabic."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', stdout=StringIO())
        cls.admin = User.objects.create_superuser('admin@x.com', 'admin@x.com', PASSWORD)
        cls.owner = Project.objects.first().owner
        cls.donor = User.objects.exclude(pk=cls.owner.pk).filter(profile__isnull=False).first()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def pages(self):
        project = Project.objects.first()
        return [
            reverse('home'), reverse('search'), reverse('search') + '?q=water', reverse('search') + '?q=مياه',
            reverse('category_projects', args=[project.category.pk]), reverse('project_detail', args=[project.pk]),
            reverse('password_reset'), reverse('password_reset_done'), reverse('password_reset_complete'),
        ]

    def private_pages(self):
        return [reverse('project_create'), reverse('my_projects'), reverse('my_donations'), reverse('profile')]

    def check_all(self, urls, language):
        self.client.post(reverse('set_language'), {'language': language, 'next': '/'})
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f'{language} {url}')
            html = response.content.decode()
            self.assertIn(f'lang="{language}"', html, url)
            self.assertNotIn('{%', html, url)      # no broken template tags
            self.assertNotIn('%(', html, url)      # no untranslated placeholders

    def test_every_page_in_both_languages_for_every_kind_of_user(self):
        for language in ['en', 'ar']:
            self.client.logout()
            self.check_all(self.pages() + [reverse('auth_page')], language)
            for user in [self.donor, self.owner, self.admin]:
                self.client.force_login(user)
                self.check_all(self.pages() + self.private_pages(), language)

    def test_admin_pages_open(self):
        self.client.force_login(self.admin)
        for model in ['project', 'category', 'tag', 'donation', 'comment', 'rating', 'projectreport', 'commentreport']:
            self.assertEqual(self.client.get(f'/admin/projects/{model}/').status_code, 200, model)
        project = Project.objects.first()
        self.assertEqual(self.client.get(f'/admin/projects/project/{project.pk}/change/').status_code, 200)

    def test_seed_demo_data_is_consistent(self):
        self.assertEqual(Project.objects.count(), 8)
        for project in Project.objects.all():
            self.assertTrue(project.images.exists(), project.title)
            self.assertTrue(project.title_ar, project.title)
            self.assertTrue(0 < project.progress_percent < 100, project.title)
        self.assertEqual(Category.objects.filter(projects__isnull=True).count(), 0)  # every category has a campaign
        # Running it again doesn't duplicate anything
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Project.objects.count(), 8)

    def test_translations_compile(self):
        out = StringIO()
        call_command('compile_translations', stdout=out)
        self.assertIn('0 missing', out.getvalue())
