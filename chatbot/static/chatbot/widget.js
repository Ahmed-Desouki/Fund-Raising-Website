(() => {
    const root = document.getElementById('chatbot');
    if (!root) return;

    const panel = document.getElementById('chatbotPanel');
    const messagesEl = document.getElementById('chatbotMessages');
    const form = document.getElementById('chatbotForm');
    const input = document.getElementById('chatbotInput');
    const csrfToken = root.querySelector('input[name=csrfmiddlewaretoken]').value;

    const STRINGS = {
        ar: {
            title: 'المساعد',
            placeholder: 'اكتب سؤالك…',
            greeting: 'أهلاً! أقدر أساعدك إزاي تتبرع، تعمل حملة، أو ألاقيلك حملة تناسبك. اسأل براحتك.',
            thinking: 'بيكتب…',
            error: 'حصلت مشكلة، جرّب تاني.',
        },
        en: {
            title: 'Help assistant',
            placeholder: 'Ask a question…',
            greeting: 'Hi! I can help you donate, start a campaign, or find a campaign you care about. Ask me anything.',
            thinking: 'Typing…',
            error: 'Something went wrong, please try again.',
        },
    };

    // Start in the site's language; the switch inside the chat can still change it
    let language = document.documentElement.lang === 'ar' ? 'ar' : 'en';
    // Conversation sent back to the server on each turn (the API is stateless)
    let history = [];

    // Builds the bubble from text nodes (never innerHTML) and turns campaign paths like /projects/3/ into links
    function setText(bubble, text) {
        bubble.textContent = '';
        let last = 0;
        for (const match of text.matchAll(/\/projects\/\d+\//g)) {
            bubble.append(text.slice(last, match.index));
            const link = document.createElement('a');
            link.href = match[0];
            link.textContent = match[0];
            bubble.append(link);
            last = match.index + match[0].length;
        }
        bubble.append(text.slice(last));
    }

    function addMessage(role, text) {
        const bubble = document.createElement('div');
        bubble.className = `chatbot-msg ${role}`;
        setText(bubble, text);
        messagesEl.appendChild(bubble);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    function setLanguage(lang) {
        language = lang;
        const s = STRINGS[lang];
        panel.dir = lang === 'ar' ? 'rtl' : 'ltr';
        panel.querySelector('[data-i18n=title]').textContent = s.title;
        input.placeholder = s.placeholder;
        root.querySelectorAll('[data-lang]').forEach(btn => btn.classList.toggle('active', btn.dataset.lang === lang));
        // Switching language starts a fresh conversation in that language
        history = [];
        messagesEl.innerHTML = '';
        addMessage('assistant', s.greeting);
    }

    document.getElementById('chatbotToggle').addEventListener('click', () => {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) input.focus();
    });
    document.getElementById('chatbotClose').addEventListener('click', () => { panel.hidden = true; });
    root.querySelectorAll('[data-lang]').forEach(btn => btn.addEventListener('click', () => setLanguage(btn.dataset.lang)));

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        addMessage('user', message);
        const pending = addMessage('assistant pending', STRINGS[language].thinking);
        form.querySelector('button').disabled = true;

        try {
            const response = await fetch(root.dataset.url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ message, history, language }),
            });
            const data = await response.json();
            pending.classList.remove('pending');
            if (response.ok) {
                setText(pending, data.reply);
                history.push({ role: 'user', content: message }, { role: 'assistant', content: data.reply });
            } else {
                pending.classList.add('error');
                pending.textContent = data.error || STRINGS[language].error;
            }
        } catch (e) {
            pending.classList.remove('pending');
            pending.classList.add('error');
            pending.textContent = STRINGS[language].error;
        } finally {
            form.querySelector('button').disabled = false;
            input.focus();
        }
    });

    setLanguage(language);
})();
