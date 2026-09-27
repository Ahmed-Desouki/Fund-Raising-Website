"""
Fills the local database with demo users, campaigns, donations, ratings and comments
so the site has something to show (e.g. on presentation day).

    python manage.py seed_demo

Demo accounts all use the password below. Never run this against a real database.
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw

from main.models import Profile
from projects.models import Category, Comment, Donation, Project, ProjectImage, Rating, Tag

DEMO_PASSWORD = 'DemoPass#2026'

USERS = [
    ('mona@demo.test', 'Mona', 'Adel', '01012345678'),
    ('omar@demo.test', 'Omar', 'Samir', '01123456789'),
    ('sara@demo.test', 'Sara', 'Hassan', '01234567890'),
    ('youssef@demo.test', 'Youssef', 'Nabil', '01567890123'),
]

PROJECTS = [
    ('Clean water for Upper Egypt villages', 'Health', 250000, ['water', 'health', 'villages'], (40, 110, 160), 4.8, True),
    ('School supplies for 500 children', 'Education', 80000, ['education', 'children'], (91, 58, 112), 4.6, True),
    ('Winter blankets for families in need', 'Charity', 60000, ['winter', 'charity', 'families'], (160, 90, 60), 4.9, True),
    ('Plant 10,000 trees in Cairo', 'Environment', 120000, ['environment', 'trees'], (50, 130, 70), 4.2, False),
    ('Coding bootcamp for girls in Aswan', 'Technology', 150000, ['education', 'technology', 'women'], (30, 30, 60), 4.4, True),
    ('Rebuild the community library in Minya', 'Community', 90000, ['education', 'community', 'books'], (120, 100, 70), 3.9, False),
    ('Street art festival in Alexandria', 'Art & Culture', 45000, ['art', 'culture'], (190, 70, 110), 4.0, True),
]

COMMENTS = [
    'This is such an important cause, happy to help!',
    'Shared with my family, hope you reach the target soon.',
    'Will there be updates on how the money is spent?',
]


def make_image(color, label):
    img = Image.new('RGB', (1200, 700), color)
    draw = ImageDraw.Draw(img)
    for i in range(0, 1200, 60):
        draw.line([(i, 700), (i + 350, 0)], fill=tuple(min(c + 25, 255) for c in color), width=18)
    draw.text((40, 640), label, fill=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, 'JPEG', quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Create demo users and campaigns for local development'

    def handle(self, *args, **options):
        users = []
        for email, first, last, mobile in USERS:
            user, created = User.objects.get_or_create(
                username=email, defaults={'email': email, 'first_name': first, 'last_name': last},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                Profile.objects.create(user=user, mobile_number=mobile)
            users.append(user)

        now = timezone.now()
        for i, (title, category, target, tags, color, rating, featured) in enumerate(PROJECTS):
            if Project.objects.filter(title=title).exists():
                continue
            owner = users[i % len(users)]
            project = Project.objects.create(
                owner=owner, title=title, category=Category.objects.get(name=category),
                details=(
                    f'{title}. Every pound goes directly to the people who need it most.\n\n'
                    'We partner with local organisations to make sure the work is done well, '
                    'and we will post regular updates with photos and receipts.'
                ),
                total_target=Decimal(target), is_featured=featured,
                start_time=now - timedelta(days=10 + i), end_time=now + timedelta(days=20 + i * 5),
            )
            project.tags.set([Tag.objects.get_or_create(name=t)[0] for t in tags])
            for n in range(3):
                shade = tuple(max(c - n * 25, 0) for c in color)
                ProjectImage(project=project).image.save(f'demo_{i}_{n}.jpg', make_image(shade, title), save=True)

            donors = [u for u in users if u != owner]
            for j, donor in enumerate(donors):
                Donation.objects.create(project=project, user=donor, amount=Decimal(target) * Decimal('0.08') * (j + 1) / 2)
                Rating.objects.create(project=project, user=donor, value=min(5, max(1, round(rating - j * 0.3))))
            comment = Comment.objects.create(project=project, user=donors[0], content=COMMENTS[i % len(COMMENTS)])
            Comment.objects.create(project=project, user=owner, parent=comment, content='Thank you so much for the support!')

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {Project.objects.count()} campaigns, {len(users)} demo users '
            f'(password is DEMO_PASSWORD in {__name__}).'
        ))
