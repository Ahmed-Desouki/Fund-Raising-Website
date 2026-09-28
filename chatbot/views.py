import json
import logging
import time

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import assistant, fallback

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_MESSAGES = 12
# Per-visitor limit so one person can't run up the API bill
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 60 * 60

RATE_LIMITED = {
    'ar': 'بعت رسايل كتير في وقت قصير. استنى شوية وجرّب تاني.',
    'en': "You've sent a lot of messages. Please wait a while and try again.",
}


def clean_history(raw):
    """Keep only well-formed recent turns so the client can't inject anything else."""
    if not isinstance(raw, list):
        return []
    history = []
    for item in raw[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role, content = item.get('role'), item.get('content')
        if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
            history.append({'role': role, 'content': content.strip()[:MAX_MESSAGE_LENGTH]})
    # The API requires the conversation to start with a user turn
    while history and history[0]['role'] != 'user':
        history.pop(0)
    return history


def within_rate_limit(session):
    now = time.time()
    recent = [t for t in session.get('chatbot_times', []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    allowed = len(recent) < RATE_LIMIT_MESSAGES
    if allowed:
        recent.append(now)
    session['chatbot_times'] = recent
    return allowed


@require_POST
def ask(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    language = data.get('language') if data.get('language') in ('ar', 'en') else 'en'
    message = data.get('message')
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({'error': 'Message is empty.'}, status=400)

    if not within_rate_limit(request.session):
        return JsonResponse({'error': RATE_LIMITED[language]}, status=429)

    history = clean_history(data.get('history'))
    history.append({'role': 'user', 'content': message.strip()[:MAX_MESSAGE_LENGTH]})

    try:
        reply = assistant.ask(history, language)
    except assistant.AssistantUnavailable as e:
        # Gemini is down or overloaded (common on the free tier): answer from the built-in help instead
        logger.warning('Chatbot using built-in answers: %s', e)
        return JsonResponse({'reply': fallback.answer(history[-1]['content'], language), 'fallback': True})

    return JsonResponse({'reply': reply})
