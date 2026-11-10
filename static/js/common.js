// ---- Offline detection (works because once the page + assets are cached/loaded,
// the app shell keeps functioning; only new-page navigation needs a connection
// to this local server) ----
function updateOnlineStatus() {
    const banner = document.getElementById('offline-banner');
    if (!banner) return;
    if (navigator.onLine) banner.classList.add('hidden');
    else banner.classList.remove('hidden');
}
window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);
document.addEventListener('DOMContentLoaded', updateOnlineStatus);

// ---- Offline-safe score submission: queue in localStorage if the request fails,
// flush the queue whenever we come back online. This is what makes the
// "AI-adaptive difficulty" keep working even with a shaky rural connection. ----
const QUEUE_KEY = 'sahayak_pending_scores';

function queueScore(payload) {
    const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    q.push(payload);
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
}

async function flushQueue() {
    const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    if (!q.length) return;
    const remaining = [];
    for (const payload of q) {
        try {
            const res = await fetch('/api/submit_score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) remaining.push(payload);
        } catch (e) {
            remaining.push(payload);
        }
    }
    localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
}
window.addEventListener('online', flushQueue);
document.addEventListener('DOMContentLoaded', flushQueue);

async function submitScore(payload) {
    try {
        const res = await fetch('/api/submit_score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('bad response');
        return await res.json();
    } catch (e) {
        queueScore(payload);
        return { ok: true, queued: true, new_level: payload.level, rolling_accuracy: payload.accuracy, reason: 'saved offline, will sync later' };
    }
}

function completeReminder(id) {
    fetch(`/api/reminder/${id}/complete`, { method: 'POST' })
        .then(() => {
            const el = document.querySelector(`.reminder-item[data-id="${id}"]`);
            if (el) el.classList.add('reminder-done');
        })
        .catch(() => {
            const el = document.querySelector(`.reminder-item[data-id="${id}"]`);
            if (el) el.classList.add('reminder-done');
        });
}

// ---- Simple voice-assist using the browser's built-in speech synthesis
// (works fully offline on most Android/desktop browsers once voices are cached) ----
const VOICE_LANG_MAP = { en: 'en-IN', hi: 'hi-IN', as: 'en-IN' }; // Assamese TTS not widely supported; falls back

function speak(text, langCode) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = VOICE_LANG_MAP[langCode] || 'en-IN';
    utter.rate = 0.9;
    window.speechSynthesis.speak(utter);
}
