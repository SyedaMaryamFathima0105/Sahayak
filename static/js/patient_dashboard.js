document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const lang = btn.dataset.lang;
        await fetch('/patient/set_language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang })
        });
        window.location.reload();
    });
});

document.querySelectorAll('.mood-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        await fetch('/patient/mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mood: btn.dataset.mood })
        });
        document.getElementById('mood-thanks').classList.remove('hidden');
    });
});

document.getElementById('speak-btn')?.addEventListener('click', () => {
    const text = document.getElementById('welcome-text').innerText;
    const currentLang = document.querySelector('.lang-btn.active')?.dataset.lang || 'en';
    speak(text, currentLang);
});
