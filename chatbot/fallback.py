"""
Built-in answers used when the AI (Gemini) is unavailable, e.g. the free tier is overloaded.

They cover the common questions about the site and recommend real campaigns from the database,
in Arabic or English, so the help chat never goes silent.
"""
import re

from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from projects.models import Category, Project

BUSY_NOTE = {
    'ar': '(المساعد الذكي عليه ضغط دلوقتي، فده رد سريع.)',
    'en': '(The smart assistant is busy right now, so this is a quick answer.)',
}

# (intent, keywords in English and Arabic)
INTENTS = [
    ('closest', ['closest', 'almost', 'nearly', 'most funded', 'اقرب', 'أقرب', 'قربت', 'خلصت تقريبا']),
    ('delete', ['delete my account', 'remove my account', 'امسح حسابي', 'احذف حسابي', 'حذف الحساب', 'مسح الحساب']),
    ('cancel', ['cancel', 'الغي', 'ألغي', 'الغاء', 'إلغاء']),
    ('start', ['start', 'create', 'my own campaign', 'new campaign', 'open a campaign', 'ابدأ', 'ابدا', 'اعمل حملة', 'أعمل حملة', 'انشئ', 'أنشئ', 'حملة جديدة', 'حمله جديده']),
    ('password', ['password', 'forgot', 'reset', 'باسورد', 'كلمة المرور', 'كلمه السر', 'نسيت']),
    ('activate', ['activate', 'activation', 'verify', 'email', 'register', 'sign up', 'signup', 'account', 'تفعيل', 'افعل', 'فعّل', 'ايميل', 'إيميل', 'سجل', 'تسجيل', 'حساب', 'اكونت', 'أكونت']),
    ('report', ['report', 'scam', 'fake', 'بلاغ', 'ابلغ', 'أبلغ', 'نصب']),
    ('donate', ['donate', 'donation', 'give', 'pay', 'اتبرع', 'أتبرع', 'تبرع', 'ادفع', 'أدفع']),
    ('rate', ['rate', 'rating', 'comment', 'reply', 'تقييم', 'اقيم', 'أقيم', 'كومنت', 'تعليق']),
    ('search', ['search', 'find', 'category', 'categories', 'ابحث', 'دور', 'بحث', 'تصنيف', 'أنواع', 'انواع']),
]

ANSWERS = {
    'donate': {
        'en': 'To donate: open a campaign, pick an amount (50, 100, 250 or 500 EGP) or type your own, and press "Donate now". You need to be logged in.',
        'ar': 'عشان تتبرع: افتح صفحة الحملة، واختار مبلغ (50 أو 100 أو 250 أو 500 جنيه) أو اكتب المبلغ اللي تحبه، ودوس "تبرّع الآن". لازم تكون عامل تسجيل دخول.',
    },
    'start': {
        'en': 'To start a campaign: log in, press "Start a campaign" at the top, then add a title, your story, a category, pictures, the target in EGP, tags and the start/end dates, and press "Publish campaign".',
        'ar': 'عشان تبدأ حملة: سجّل دخول، ودوس "ابدأ حملة" فوق، واكتب العنوان والقصة واختار التصنيف والصور والمبلغ المستهدف بالجنيه والوسوم وتاريخ البداية والنهاية، ودوس "نشر الحملة".',
    },
    'cancel': {
        'en': 'The owner of a campaign can cancel it from the campaign page, but only while donations are still under 25% of the target.',
        'ar': 'صاحب الحملة يقدر يلغيها من صفحة الحملة، بس طول ما التبرعات لسه أقل من 25% من المبلغ المستهدف.',
    },
    'activate': {
        'en': 'After you register, we email you an activation link that works for 24 hours. Check your inbox and Spam folder. No email? Try to log in and press "Send it again".',
        'ar': 'بعد ما تسجّل، بنبعتلك لينك تفعيل على الإيميل صالح لمدة 24 ساعة. بص في الـ Inbox والـ Spam. موصلكش؟ جرّب تعمل تسجيل دخول ودوس "ابعته تاني".',
    },
    'password': {
        'en': 'Forgot your password? On the login page press "Forgot password?", enter your email, and we will send you a link to choose a new one.',
        'ar': 'نسيت كلمة المرور؟ في صفحة تسجيل الدخول دوس "نسيت كلمة المرور؟"، واكتب إيميلك، وهيوصلك لينك تختار منه كلمة مرور جديدة.',
    },
    'delete': {
        'en': 'To delete your account: open your profile, press "Delete my account" and confirm with your password. This cannot be undone.',
        'ar': 'عشان تحذف حسابك: افتح صفحة حسابك، ودوس "احذف حسابي"، وأكّد بكلمة المرور. مش هينفع ترجع فيها بعد كده.',
    },
    'report': {
        'en': 'If a campaign or comment looks wrong, open it and press "Report", write the reason, and our team will review it.',
        'ar': 'لو حملة أو تعليق شكله مش مظبوط، افتحه ودوس "إبلاغ"، واكتب السبب، وفريقنا هيراجعه.',
    },
    'rate': {
        'en': 'On any campaign page you can rate it from 1 to 5 stars, write a comment and reply to other comments. You need to be logged in.',
        'ar': 'في صفحة أي حملة تقدر تقيّمها من 1 لـ 5 نجوم، وتكتب تعليق وترد على التعليقات. لازم تكون عامل تسجيل دخول.',
    },
    'search': {
        'en': 'Use the search bar at the top to find campaigns by title or tag, or browse by category on the home page.',
        'ar': 'استخدم خانة البحث اللي فوق عشان تلاقي حملة بالعنوان أو الوسم، أو تصفّح حسب التصنيف في الصفحة الرئيسية.',
    },
    'help': {
        'en': 'I can help you donate, start or cancel a campaign, activate your account, reset your password, or find a campaign. For example, ask "How do I donate?" or "Recommend an education campaign".',
        'ar': 'أقدر أساعدك تتبرع، أو تبدأ حملة أو تلغيها، أو تفعّل حسابك، أو ترجّع كلمة المرور، أو تلاقي حملة. مثلاً اسأل "إزاي أتبرع؟" أو "رشحلي حملة تعليم".',
    },
}

RECOMMEND_INTRO = {
    'en': 'Here are campaigns you might like:',
    'ar': 'دي حملات ممكن تعجبك:',
}
NO_MATCH = {
    'en': "I couldn't find a campaign about that on the site right now. Try the search bar, or browse the categories on the home page.",
    'ar': 'ملقتش حملة عن الموضوع ده على الموقع دلوقتي. جرّب خانة البحث، أو تصفّح التصنيفات في الصفحة الرئيسية.',
}
ASKS_FOR_CAMPAIGN = ['campaign', 'project', 'recommend', 'حمله', 'حملات', 'مشروع', 'رشح']
CLOSEST_INTRO = {
    'en': 'These campaigns are closest to their goal:',
    'ar': 'دي الحملات الأقرب لهدفها:',
}


def normalize(text):
    text = text.lower()
    return re.sub('[إأآ]', 'ا', text).replace('ة', 'ه').replace('ى', 'ي')


def open_campaigns():
    now = timezone.now()
    return list(Project.objects.filter(is_cancelled=False, start_time__lte=now, end_time__gte=now)
                .select_related('category').prefetch_related('tags'))


def describe(project, language):
    with translation.override(language):
        title = project.display_title
    percent = f'{project.progress_percent}%'
    return f'- {title} ({percent}) {reverse("project_detail", args=[project.pk])}'


def matching_campaigns(message, campaigns):
    """Campaigns whose category (in English or Arabic), tags or title words appear in the message."""
    text = normalize(message)
    scored = []
    for project in campaigns:
        words = {normalize(project.category.name)}
        with translation.override('ar'):
            words.add(normalize(_(project.category.name)).removeprefix('ال'))
        words |= {normalize(tag.name) for tag in project.tags.all()}
        words |= {normalize(w) for w in re.findall(r'\w{4,}', f'{project.title} {project.title_ar}')}
        score = sum(1 for w in words if w and w in text)
        if score:
            scored.append((score, project.progress_percent, project))
    return [p for _, _, p in sorted(scored, key=lambda s: (-s[0], -s[1]))]


def answer(message, language):
    text = normalize(message)
    campaigns = open_campaigns()
    intent = next((name for name, keywords in INTENTS if any(normalize(k) in text for k in keywords)), None)
    lines = []

    if intent == 'closest':
        top = sorted(campaigns, key=lambda p: -p.progress_percent)[:3]
        lines = [CLOSEST_INTRO[language]] + [describe(p, language) for p in top]
    else:
        matches = matching_campaigns(message, campaigns)[:3]
        if intent:
            lines.append(ANSWERS[intent][language])
        if matches:
            lines += [RECOMMEND_INTRO[language]] + [describe(p, language) for p in matches]
        elif not intent and any(normalize(w) in text for w in ASKS_FOR_CAMPAIGN):
            # Asked about a campaign we don't have: say so instead of inventing one
            lines.append(NO_MATCH[language])
        if not lines:
            lines.append(ANSWERS['help'][language])

    lines.append(BUSY_NOTE[language])
    return '\n'.join(lines)
