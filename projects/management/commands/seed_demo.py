"""
Fills the local database with demo users, campaigns, donations, ratings and comments
so the site has something to show (e.g. on presentation day).

    python manage.py seed_demo            # add anything that's missing
    python manage.py seed_demo --reset    # delete the demo campaigns and recreate them

The campaigns are realistic examples, not real fundraisers. Their photos are real,
freely licensed pictures from Wikimedia Commons: see projects/demo_images/CREDITS.md.

Demo accounts all use the password below. Never run this against a real database.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import Profile
from projects.models import Category, Comment, Donation, Project, ProjectImage, Rating, Tag

DEMO_PASSWORD = 'DemoPass#2026'
IMAGES_DIR = Path(__file__).resolve().parents[2] / 'demo_images'

USERS = [
    ('mona@demo.test', 'Mona', 'Adel', '01012345678'),
    ('omar@demo.test', 'Omar', 'Samir', '01123456789'),
    ('sara@demo.test', 'Sara', 'Hassan', '01234567890'),
    ('youssef@demo.test', 'Youssef', 'Nabil', '01567890123'),
    ('nour@demo.test', 'Nour', 'Ibrahim', '01098765432'),
    ('karim@demo.test', 'Karim', 'Mostafa', '01187654321'),
    ('hana@demo.test', 'Hana', 'Fathy', '01276543210'),
    ('ali@demo.test', 'Ali', 'Mahmoud', '01565432109'),
]

PROJECTS = [
    {
        'title': 'Clean drinking water for villages in Qena',
        'title_ar': 'مياه شرب نظيفة لقرى قنا',
        'details_ar': 'بيوت كتير في القرى الصغيرة على النيل في قنا لسه بتاخد المياه من الترعة أو من طلمبات قديمة مياهها في الغالب ملوثة، والأطفال هما أول ناس بيتعبوا.\n\nهنركّب 12 نقطة مياه بفلاتر ونوصّلها بالخط الرئيسي، كل نقطة بتخدم حوالي 40 أسرة. الميزانية بتغطي المواسير والفلاتر والعمالة وتغيير الفلاتر لمدة سنة.\n\nهننشر صور كل نقطة مياه أول ما تخلص.',
        'category': 'Community', 'target': 250000, 'funded': 0.62, 'featured': True, 'rating': 5,
        'tags': ['water', 'villages', 'upper egypt'], 'images': ['water-1'], 'days': (35, 40),
        'details': (
            'Many homes in small villages along the Nile in Qena still draw water from the canal or from old hand pumps '
            'that are often contaminated. Children are the first to get sick.\n\n'
            'We will install 12 filtered water points and connect them to the main line, each serving around 40 families. '
            'The budget covers pipes, filters, labour and one year of filter replacements.\n\n'
            'We will post photos of every water point as it is finished.'
        ),
    },
    {
        'title': 'School bags and supplies for 500 first graders',
        'title_ar': 'شنط وأدوات مدرسية لـ 500 طفل في أولى ابتدائي',
        'details_ar': 'لأسر كتير في مناطق القاهرة المزدحمة، شنطة المدرسة والكشاكيل والزي لطفل في أولى ابتدائي بتكلّف أكتر من دخل أسبوع كامل.\n\nكل 180 جنيه بتوفر شنطة كاملة: شنطة وكشاكيل وأقلام وألوان وعلبة أكل. بنشتغل مع 4 مدارس ابتدائي حكومي عشان نوصل لـ 500 طفل قبل بداية الترم التاني.',
        'category': 'Education', 'target': 90000, 'funded': 0.84, 'featured': True, 'rating': 5,
        'tags': ['education', 'children', 'school'], 'images': ['school-1', 'school-2'], 'days': (20, 15),
        'details': (
            'For many families in Cairo\'s crowded neighbourhoods, buying a school bag, notebooks and a uniform for a '
            'first grader costs more than a week\'s income.\n\n'
            'Each 180 EGP pays for one full starter kit: a bag, notebooks, pencils, colours and a lunch box. We are '
            'working with four public primary schools to reach 500 children before the second term starts.'
        ),
    },
    {
        'title': 'Winter blankets for 300 families in Aswan',
        'title_ar': 'بطاطين الشتا لـ 300 أسرة في أسوان',
        'details_ar': 'ليالي الصحرا حوالين أسوان بتبقى برد جداً في ديسمبر ويناير، وأسر كتير في القرى اللي حوالين المدينة معندهاش بطاطين تكفي كل أفرادها.\n\nكل 200 جنيه بتشتري بطانية تقيلة. متطوعين من القرى هيوزعوها بنفسهم، ونبدأ بالأسر اللي فيها كبار سن أو أطفال صغيرين.',
        'category': 'Charity', 'target': 60000, 'funded': 0.91, 'featured': True, 'rating': 5,
        'tags': ['winter', 'families', 'upper egypt'], 'images': ['winter-1'], 'days': (25, 10),
        'details': (
            'Desert nights around Aswan get surprisingly cold in December and January, and many families in the '
            'villages outside the city don\'t have enough blankets for everyone.\n\n'
            'Every 200 EGP buys one thick blanket. Volunteers from the villages will hand them out directly, '
            'starting with families that have elderly members or small children.'
        ),
    },
    {
        'title': 'Clean up the Nile banks in Cairo',
        'title_ar': 'تنظيف ضفاف النيل في القاهرة',
        'details_ar': 'زجاجات وأكياس البلاستيك بتتجمع على ضفاف النيل كل أسبوع. بننظم يوم تنظيف كل شهر مع متطوعين من المنطقة والمدارس.\n\nتبرعك بيغطي الجوانتيات والأكياس وأدوات الأمان وإيجار المراكب للجزر وإعادة تدوير اللي بنجمعه. هدفنا 12 يوم تنظيف السنة دي و100 صندوق زبالة جديد على الكورنيش.',
        'category': 'Environment', 'target': 75000, 'funded': 0.37, 'featured': False, 'rating': 4,
        'tags': ['environment', 'nile', 'volunteering'], 'images': ['nile-1', 'nile-2'], 'days': (12, 50),
        'details': (
            'Plastic bottles and bags pile up along the Nile banks every week. We are organising monthly clean-up days '
            'with local volunteers and schools.\n\n'
            'Your donation covers gloves, bags, safety gear, boat rental for the islands and proper recycling of what we '
            'collect. The goal is 12 clean-up days this year and 100 new trash bins along the corniche.'
        ),
    },
    {
        'title': 'Coding classes for girls in Aswan',
        'title_ar': 'كورسات برمجة للبنات في أسوان',
        'details_ar': 'نادراً ما البنات في أسوان بياخدوا فرصة يتعلموا برمجة، وعايزين نغير ده بكورس مجاني لمدة 6 شهور في تطوير المواقع لـ 60 طالبة ثانوي وجامعة.\n\nالميزانية بتدفع تمن 20 لابتوب مجدد، والإنترنت، ومدرّبين اتنين، ومواصلات الطالبات من القرى القريبة. مشروع التخرج هيبقى مواقع حقيقية لمحلات وشركات صغيرة في المنطقة.',
        'category': 'Technology', 'target': 150000, 'funded': 0.55, 'featured': True, 'rating': 4,
        'tags': ['education', 'technology', 'girls', 'upper egypt'], 'images': ['coding-1', 'coding-2'], 'days': (30, 45),
        'details': (
            'Girls in Aswan rarely get the chance to learn programming. We want to change that with a free six-month '
            'course in web development for 60 high-school and university students.\n\n'
            'The budget pays for 20 refurbished laptops, internet, two instructors and transport for students from '
            'nearby villages. Graduates will build real websites for local businesses as their final project.'
        ),
    },
    {
        'title': 'A reading room for children in Alexandria',
        'title_ar': 'غرفة قراءة للأطفال في الإسكندرية',
        'details_ar': 'بنحوّل أوضة فاضية في مركز خدمة مجتمعية في الإسكندرية لغرفة قراءة هادية ومنورة للأطفال من 6 لـ 14 سنة.\n\nالفلوس هتشتري رفوف وترابيزات ومخدات و1,500 كتاب أطفال عربي وإنجليزي، وهتدفع مرتب أمين مكتبة يعمل ساعة حكايات كل أسبوع لمدة سنة.',
        'category': 'Education', 'target': 45000, 'funded': 0.18, 'featured': False, 'rating': 4,
        'tags': ['education', 'children', 'books'], 'images': ['reading-1', 'reading-2'], 'days': (5, 60),
        'details': (
            'We are turning an empty room in a community centre in Alexandria into a bright, quiet reading room for '
            'children aged 6 to 14.\n\n'
            'The money buys shelves, tables, cushions, 1,500 Arabic and English children\'s books, and pays a librarian '
            'to run weekly story hours for the first year.'
        ),
    },
    {
        'title': 'Oud and music lessons for kids in Old Cairo',
        'title_ar': 'دروس عود وموسيقى للأطفال في مصر القديمة',
        'details_ar': 'دروس الموسيقى رفاهية أغلب الأسر في مصر القديمة مش قادرة عليها. عايزين نقدّم دروس عود وإيقاع مجانية كل أسبوع لـ 40 طفل لمدة سنة كاملة.\n\nالتبرعات بتدفع تمن آلات الأطفال هياخدوها معاهم، ومدرّسين موسيقى اتنين، وحفلة آخر السنة يعزفوا فيها قدام أهاليهم.',
        'category': 'Art & Culture', 'target': 55000, 'funded': 0.46, 'featured': True, 'rating': 5,
        'tags': ['music', 'culture', 'children'], 'images': ['music-1', 'music-2'], 'days': (18, 30),
        'details': (
            'Music lessons are a luxury most families in Old Cairo can\'t afford. We want to offer free weekly oud and '
            'percussion lessons to 40 children for a full year.\n\n'
            'Donations pay for instruments the children can keep, two music teachers and an end-of-year concert where '
            'the students perform for their families.'
        ),
    },
    {
        'title': 'Mobile medical day for villages in Qena',
        'title_ar': 'يوم طبي متنقل لقرى قنا',
        'details_ar': 'أقرب مستشفى لقرى كتير في قنا على بُعد أكتر من ساعة. مرة كل شهر، فريق من الدكاترة المتطوعين هيعمل عيادة مجانية يوم كامل: كشف عام وصحة أطفال وكشف نظر وأدوية أساسية.\n\nتبرعك بيغطي الأدوية ومواصلات الفريق الطبي والمتابعة للمرضى اللي محتاجين.',
        'category': 'Health', 'target': 120000, 'funded': 0.73, 'featured': False, 'rating': 5,
        'tags': ['health', 'villages', 'upper egypt'], 'images': ['water-2'], 'days': (28, 22),
        'details': (
            'The nearest hospital is more than an hour away for many villages in Qena. Once a month, a team of '
            'volunteer doctors will set up a free clinic for a full day: general check-ups, children\'s health, eye '
            'exams and basic medicines.\n\n'
            'Your donation covers medicines, transport for the medical team and follow-up visits for patients who need them.'
        ),
    },
]

# Titles used by older versions of this command, removed by --reset
OLD_TITLES = [
    'Clean water for Upper Egypt villages', 'School supplies for 500 children', 'Winter blankets for families in need',
    'Plant 10,000 trees in Cairo', 'Coding bootcamp for girls in Aswan', 'Rebuild the community library in Minya',
    'Street art festival in Alexandria',
]

COMMENTS = [
    ('Such an important cause. Shared it with my family!', 'Thank you so much, every share helps.'),
    ('Will you post updates on how the money is spent?', 'Yes, we will post photos and receipts every two weeks.'),
    ('I donated last year to something similar, happy to help again.', 'We really appreciate your support!'),
]


class Command(BaseCommand):
    help = 'Create demo users and campaigns for local development'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete the demo campaigns first and recreate them')

    def handle(self, *args, **options):
        if options['reset']:
            Project.objects.filter(title__in=[p['title'] for p in PROJECTS] + OLD_TITLES).delete()

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
        for i, p in enumerate(PROJECTS):
            if Project.objects.filter(title=p['title']).exists():
                continue
            owner = users[i % len(users)]
            started_days_ago, days_left = p['days']
            project = Project.objects.create(
                owner=owner, title=p['title'], details=p['details'], title_ar=p['title_ar'], details_ar=p['details_ar'],
                category=Category.objects.get(name=p['category']),
                total_target=Decimal(p['target']), is_featured=p['featured'],
                start_time=now - timedelta(days=started_days_ago), end_time=now + timedelta(days=days_left),
            )
            project.tags.set([Tag.objects.get_or_create(name=t)[0] for t in p['tags']])
            for name in p['images']:
                with open(IMAGES_DIR / f'{name}.jpg', 'rb') as f:
                    ProjectImage(project=project).image.save(f'demo_{name}.jpg', File(f), save=True)

            # Spread the funded amount over a varying number of donors, in round numbers
            donors = [u for u in users if u != owner][: 3 + i % 5]
            weights = list(range(1, len(donors) + 1))
            raised = Decimal(p['target']) * Decimal(str(p['funded']))
            for donor, weight in zip(donors, weights):
                amount = (raised * weight / sum(weights) / 50).quantize(Decimal('1')) * 50
                Donation.objects.create(project=project, user=donor, amount=max(amount, Decimal('50')))
            for n, donor in enumerate(donors):
                Rating.objects.create(project=project, user=donor, value=p['rating'] if n % 3 else max(p['rating'] - 1, 1))

            question, answer = COMMENTS[i % len(COMMENTS)]
            comment = Comment.objects.create(project=project, user=donors[0], content=question)
            Comment.objects.create(project=project, user=owner, parent=comment, content=answer)

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {Project.objects.count()} campaigns, {len(users)} demo users '
            f'(password is DEMO_PASSWORD in {__name__}).'
        ))
