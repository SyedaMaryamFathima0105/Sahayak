# Sahayak — AI Cognitive Care Platform for NER Dementia Patients

Working prototype for the SIH-style problem statement on AI-enabled cognitive
gaming for elderly dementia patients in the North Eastern Region.

## What's implemented in this prototype
- **3 adaptive cognitive games**: Memory Match (pattern/object recognition),
  Focus & Attention (Simon-says sequence recall), Daily Routine Recall.
- **Rule-based adaptive difficulty engine** (`update_difficulty` in `app.py`):
  tracks rolling accuracy + response time per patient per game and raises/lowers
  a 1–5 difficulty level — a lightweight stand-in for a trained ML model,
  with the same input/output contract so it can be swapped for a real
  classifier later without touching the games or UI.
- **Multilingual UI**: English / Hindi / Assamese string dictionaries
  (`LANGUAGES` in `app.py`) plus browser-based text-to-speech (Web Speech API)
  for voice-assisted reading of prompts — no internet required after page load.
- **Reminders system**: medicine / hydration / activity / appointment,
  caregiver-managed, patient marks them done.
- **Caregiver dashboard**: multi-patient overview, 7-day accuracy trend,
  missed-reminder and low-performance alerts, per-patient detail page with
  a Chart.js performance graph and mood-log history.
- **Offline resilience**: game scores queue in `localStorage` and auto-sync
  when connectivity returns (`common.js`) — relevant for low-connectivity
  rural deployment. Because the whole stack is a local Flask server + SQLite
  file, it also runs with zero internet dependency on a local device/kiosk.
- **Elderly-friendly UI**: large text, big tap targets, high contrast,
  minimal navigation depth, emoji/icon-first design.
- **Mood check-in**: simple daily emotional-state log feeding into the
  caregiver view.

## What's stubbed / next steps for a production build
- Real ML model (e.g. Bayesian knowledge tracing or a small classifier) in
  place of the rule-based adaptive engine — the schema already captures
  accuracy, response time, and level per session for training one.
- Proper voice **input** (speech-to-text) for hands-free play — only
  voice *output* (TTS) is wired up here.
- Full offline-first PWA (service worker + IndexedDB) instead of the
  localStorage queue used here.
- Real regional-language translations reviewed by native speakers (Assamese,
  Khasi, Bodo, Manipuri, etc.) — only sample Hindi/Assamese strings included.
- Push notifications for reminders (currently an in-app list only).
- Authentication hardening (PIN-only login is for demo purposes).

## Running it
```bash
pip install -r requirements.txt
python3 app.py
```
Then visit http://localhost:5000 (the database seeds itself with demo data
on first run).

### Demo logins
- Patients: PIN `1111` (Ratan Gogoi), PIN `2222` (Mema Lyngdoh)
- Caregivers: PIN `9999` (ASHA/health worker), PIN `5555` (family member)

## Project structure
```
app.py                       - routes, adaptive difficulty engine
database.py                  - SQLite schema + demo seed data
templates/                   - Jinja2 templates (patient + caregiver views, 3 games)
static/css/style.css         - elderly-friendly styling
static/js/common.js          - offline queueing, text-to-speech, shared helpers
static/js/patient_dashboard.js
```
