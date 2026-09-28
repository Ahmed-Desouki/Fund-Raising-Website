"""
Talks to Claude on behalf of the site's help bot.

The bot answers questions about the platform (how to register, donate, start a
campaign, ...) and about the campaigns currently on the site, in Arabic or English.
"""
import anthropic
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from projects.models import Category, Project

MODEL = 'claude-opus-5'
MAX_CAMPAIGNS_IN_CONTEXT = 30

SYSTEM_PROMPT = """You are the help assistant for "Fundraiser", a crowdfunding website for charity and community projects in Egypt.

Help visitors with:
- How the site works: registering (activation link sent by email, valid for 24 hours), logging in with email and password, editing their profile, deleting their account.
- Starting a campaign: logged-in users click "Start a campaign" and enter a title, details, category, pictures, a target in EGP, tags and start/end dates.
- Donating: open a campaign page, pick or type an amount in EGP and press Donate. Users can also rate, comment, reply and report inappropriate campaigns or comments.
- Cancelling: a campaign owner can cancel it only while donations are under 25% of the target.
- Finding campaigns: the search bar searches by title or tag, and each category has its own page.
- Recommending campaigns from the list below that match what the visitor cares about. Link to a campaign with its path, e.g. /projects/3/.

Only state facts about campaigns that appear in the list below; if something isn't there, say you don't know. You cannot donate, create accounts or change anything on the site yourself; explain the steps instead. Never ask for passwords or payment details. If a question is unrelated to the site or to charity and fundraising, briefly say you can only help with this website.

Keep answers short and friendly: a few sentences or a short list, plain text without markdown headings."""

LANGUAGE_INSTRUCTIONS = {
    'ar': 'Reply in Egyptian Arabic, written in Arabic script.',
    'en': 'Reply in English.',
}


def campaigns_context():
    """A compact, deterministic list of what's on the site right now."""
    now = timezone.now()
    lines = ['Categories: ' + ', '.join(Category.objects.values_list('name', flat=True))]
    lines.append('Campaigns (title | category | raised / target EGP | days left | tags | path):')
    projects = (
        Project.objects.filter(is_cancelled=False, end_time__gte=now)
        .select_related('category').prefetch_related('tags')
        .order_by('pk')[:MAX_CAMPAIGNS_IN_CONTEXT]
    )
    for p in projects:
        tags = ', '.join(sorted(t.name for t in p.tags.all()))
        lines.append(
            f'- {p.title} | {p.category.name} | {p.total_donations:.0f} / {p.total_target:.0f} '
            f'| {p.days_left} | {tags} | {reverse("project_detail", args=[p.pk])}'
        )
    if len(lines) == 2:
        lines.append('- (no active campaigns right now)')
    return '\n'.join(lines)


class AssistantUnavailable(Exception):
    """Raised when the bot can't produce an answer (no key, API down, refusal...)."""


def ask(history, language):
    """
    history: list of {"role": "user"|"assistant", "content": str}, ending with the user's message.
    Returns the assistant's reply text.
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise AssistantUnavailable('ANTHROPIC_API_KEY is not set')

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    system = [
        # Stable instructions first so they can be cached across visitors
        {'type': 'text', 'text': SYSTEM_PROMPT, 'cache_control': {'type': 'ephemeral'}},
        {'type': 'text', 'text': campaigns_context()},
        {'type': 'text', 'text': LANGUAGE_INSTRUCTIONS[language]},
    ]
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            messages=history,
            # Chat answers don't need deep reasoning; low effort keeps replies fast and cheap
            output_config={'effort': 'low'},
            # If a request is declined, let the API retry it on a suitable fallback model
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
        )
    except anthropic.APIConnectionError as e:
        raise AssistantUnavailable('Could not reach the Claude API') from e
    except anthropic.RateLimitError as e:
        raise AssistantUnavailable('Rate limited by the Claude API') from e
    except anthropic.APIStatusError as e:
        raise AssistantUnavailable(f'Claude API error {e.status_code}') from e

    if response.stop_reason == 'refusal':
        raise AssistantUnavailable('Request was declined')

    text = ''.join(block.text for block in response.content if block.type == 'text').strip()
    if not text:
        raise AssistantUnavailable('Empty response')
    return text
