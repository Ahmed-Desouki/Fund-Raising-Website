import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Category, Comment, Donation, Project, Rating

TEMP_MEDIA = tempfile.mkdtemp()


def make_image(name='test.png'):
    buf = BytesIO()
    Image.new('RGB', (10, 10), 'purple').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProjectTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = User.objects.create_user('owner@x.com', 'owner@x.com', 'pass12345!')
        self.donor = User.objects.create_user('donor@x.com', 'donor@x.com', 'pass12345!')
        self.category = Category.objects.get(name='Health')
        now = timezone.now()
        self.project = Project.objects.create(
            owner=self.owner, title='Clean water', details='Wells', category=self.category,
            total_target=Decimal('1000'), start_time=now - timedelta(days=1), end_time=now + timedelta(days=30),
        )

    def test_create_project_with_images_and_tags(self):
        self.client.force_login(self.owner)
        now = timezone.now()
        response = self.client.post(reverse('project_create'), {
            'title': 'School books', 'details': 'Books for kids', 'category': self.category.pk,
            'total_target': '5000',
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M'),
            'tags': 'Education, kids, education',
            'images': [make_image('a.png'), make_image('b.png')],
        })
        project = Project.objects.get(title='School books')
        self.assertRedirects(response, reverse('project_detail', args=[project.pk]))
        self.assertEqual(project.images.count(), 2)
        self.assertEqual(sorted(project.tags.values_list('name', flat=True)), ['education', 'kids'])

    def test_end_must_be_after_start(self):
        self.client.force_login(self.owner)
        now = timezone.now()
        response = self.client.post(reverse('project_create'), {
            'title': 'Bad dates', 'details': 'x', 'category': self.category.pk, 'total_target': '100',
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'images': [make_image()],
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(title='Bad dates').exists())

    def test_donate(self):
        self.client.force_login(self.donor)
        self.client.post(reverse('donate', args=[self.project.pk]), {'amount': '150'})
        self.assertEqual(self.project.total_donations, Decimal('150'))

    def test_cannot_donate_to_cancelled_project(self):
        self.project.is_cancelled = True
        self.project.save()
        self.client.force_login(self.donor)
        self.client.post(reverse('donate', args=[self.project.pk]), {'amount': '150'})
        self.assertEqual(Donation.objects.count(), 0)

    def test_owner_can_cancel_under_25_percent(self):
        Donation.objects.create(project=self.project, user=self.donor, amount=Decimal('249'))
        self.client.force_login(self.owner)
        self.client.post(reverse('cancel_project', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_cancelled)

    def test_owner_cannot_cancel_at_25_percent(self):
        Donation.objects.create(project=self.project, user=self.donor, amount=Decimal('250'))
        self.client.force_login(self.owner)
        self.client.post(reverse('cancel_project', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_cancelled)

    def test_non_owner_cannot_cancel(self):
        self.client.force_login(self.donor)
        response = self.client.post(reverse('cancel_project', args=[self.project.pk]))
        self.assertEqual(response.status_code, 404)

    def test_rating_is_updated_not_duplicated(self):
        self.client.force_login(self.donor)
        self.client.post(reverse('rate_project', args=[self.project.pk]), {'value': 2})
        self.client.post(reverse('rate_project', args=[self.project.pk]), {'value': 5})
        self.assertEqual(Rating.objects.get().value, 5)

    def test_comment_and_reply(self):
        self.client.force_login(self.donor)
        self.client.post(reverse('add_comment', args=[self.project.pk]), {'content': 'Great cause'})
        parent = Comment.objects.get()
        self.client.post(reverse('add_comment', args=[self.project.pk]), {'content': 'Agreed', 'parent_id': parent.pk})
        self.assertEqual(parent.replies.count(), 1)

    def test_search_by_title_and_tag(self):
        self.project.tags.create(name='water')
        self.assertContains(self.client.get(reverse('search'), {'q': 'clean'}), 'Clean water')
        self.assertContains(self.client.get(reverse('search'), {'q': 'water'}), 'Clean water')
        self.assertNotContains(self.client.get(reverse('search'), {'q': 'nothing'}), 'Clean water')

    def test_pages_render(self):
        Rating.objects.create(project=self.project, user=self.donor, value=4)
        self.client.force_login(self.donor)
        for url in [reverse('home'), reverse('project_detail', args=[self.project.pk]),
                    reverse('category_projects', args=[self.category.pk]), reverse('my_projects'),
                    reverse('my_donations'), reverse('project_create')]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse('project_create'))
        self.assertRedirects(response, f"{reverse('auth_page')}?next={reverse('project_create')}")

    def test_donor_count_and_days_left(self):
        Donation.objects.create(project=self.project, user=self.donor, amount=Decimal('10'))
        Donation.objects.create(project=self.project, user=self.donor, amount=Decimal('20'))
        self.assertEqual(self.project.donor_count, 1)
        self.assertIn(self.project.days_left, (29, 30))
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertContains(response, 'Recent donations')
        self.assertContains(response, 'wa.me')
