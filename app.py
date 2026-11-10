from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import get_db, init_db
from datetime import datetime
import statistics

app = Flask(__name__)
app.secret_key = "ner-cognitive-care-prototype-secret"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 365

LANGUAGES = {
    "en": {"app_name": "Sahayak - Cognitive Care", "welcome": "Welcome", "play": "Play", "memory_game": "Memory Match", "attention_game": "Focus & Attention", "routine_game": "Daily Routine", "orientation_game": "Day & Place", "language_game": "Word Finder", "visual_game": "Shape & Space", "numbers_game": "Number Trail", "reminders": "My Reminders", "well_done": "Well done!", "try_again": "Try that again!"},
    "hi": {"app_name": "सहायक - संज्ञानात्मक देखभाल", "welcome": "स्वागत है", "play": "खेलें", "memory_game": "याददाश्त खेल", "attention_game": "ध्यान अभ्यास", "routine_game": "दैनिक दिनचर्या", "orientation_game": "दिन और जगह", "language_game": "शब्द खोज", "visual_game": "आकार और स्थान", "numbers_game": "संख्या पथ", "reminders": "मेरे रिमाइंडर", "well_done": "बहुत बढ़िया!", "try_again": "कोई बात नहीं, फिर कोशिश करें!"},
    "as": {"app_name": "সহায়ক - স্মৃতি যত্ন", "welcome": "স্বাগতম", "play": "খেলক", "memory_game": "স্মৃতি মিলাওক", "attention_game": "মনোযোগ অনুশীলন", "routine_game": "দৈনন্দিন কাম", "orientation_game": "দিন আৰু ঠাই", "language_game": "শব্দ বিচাৰ", "visual_game": "আকাৰ আৰু স্থান", "numbers_game": "সংখ্যা পথ", "reminders": "মোৰ ৰিমাইণ্ডাৰ", "well_done": "বহুত ভাল!", "try_again": "পুনৰ চেষ্টা কৰক!"},
}


def update_difficulty(patient_id, game_type, accuracy, avg_time_ms):
    conn = get_db(); c = conn.cursor()
    recent = [r["accuracy"] for r in c.execute("SELECT accuracy FROM game_sessions WHERE patient_id=? AND game_type=? ORDER BY played_at DESC LIMIT 2", (patient_id, game_type)).fetchall()]
    recent.append(accuracy)
    rolling_acc = statistics.mean(recent)
    row = c.execute("SELECT level FROM difficulty WHERE patient_id=? AND game_type=?", (patient_id, game_type)).fetchone()
    level = row["level"] if row else 1
    reason = "held steady"
    if rolling_acc >= .8 and avg_time_ms < 6000 and level < 5:
        level += 1; reason = "increased — strong recent performance"
    elif rolling_acc <= .45 and level > 1:
        level -= 1; reason = "decreased — reducing cognitive load"
    c.execute("INSERT INTO difficulty VALUES (?,?,?) ON CONFLICT(patient_id, game_type) DO UPDATE SET level=excluded.level", (patient_id, game_type, level))
    conn.commit(); conn.close()
    return level, round(rolling_acc, 2), reason


def patient_by_name(name):
    conn = get_db()
    p = conn.execute("SELECT * FROM patients WHERE lower(name)=lower(?)", (name.strip(),)).fetchone()
    conn.close(); return p


def ensure_patient_access(pid, caregiver_id):
    conn = get_db()
    ok = conn.execute("SELECT 1 FROM patient_caregiver WHERE patient_id=? AND caregiver_id=?", (pid, caregiver_id)).fetchone()
    conn.close(); return bool(ok)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/patient")
def patient_entry():
    return render_template("patient_register.html")


@app.route("/patient/login", methods=["POST"])
def patient_login():
    name = request.form.get("name", "").strip()
    if len(name) < 2:
        return render_template("patient_register.html", error="Please enter your name.")
    patient = patient_by_name(name)
    if not patient:
        return render_template("patient_register.html", error="We couldn't find that patient. You can register a new profile.", name=name)
    session.clear(); session.permanent = True; session["patient_id"] = patient["id"]
    conn = get_db(); conn.execute("UPDATE patients SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (patient["id"],)); conn.commit(); conn.close()
    return redirect(url_for("patient_dashboard"))


@app.route("/patient/register", methods=["POST"])
def patient_register():
    name = request.form.get("name", "").strip(); language = request.form.get("language", "en"); avatar = request.form.get("avatar", "👤")
    if len(name) < 2:
        return render_template("patient_register.html", error="Please enter a name.", name=name)
    if patient_by_name(name):
        return render_template("patient_register.html", error="A profile with that name already exists. Choose 'Sign in' to continue.", name=name)
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO patients (name, pin, language, avatar, last_seen) VALUES (?,?,?,?,?)", (name, "", language if language in LANGUAGES else "en", avatar, datetime.now().isoformat(timespec="seconds")))
    pid = c.lastrowid
    for g in ("memory", "attention", "routine", "orientation", "language", "visual", "numbers"):
        c.execute("INSERT INTO difficulty VALUES (?,?,1)", (pid, g))
    caregiver = c.execute("SELECT id FROM caregivers ORDER BY id LIMIT 1").fetchone()
    if caregiver: c.execute("INSERT OR IGNORE INTO patient_caregiver VALUES (?,?)", (pid, caregiver["id"]))
    conn.commit(); conn.close()
    session.clear(); session.permanent = True; session["patient_id"] = pid
    return redirect(url_for("patient_dashboard"))


@app.route("/caregiver/login", methods=["POST"])
def caregiver_login():
    pin = request.form.get("pin", "")
    conn = get_db(); cg = conn.execute("SELECT * FROM caregivers WHERE pin=?", (pin,)).fetchone(); conn.close()
    if cg:
        session.clear(); session.permanent = True; session["caregiver_id"] = cg["id"]; return redirect(url_for("caregiver_dashboard"))
    return render_template("index.html", error="Caregiver PIN not recognized.")


@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))


@app.route("/patient/dashboard")
def patient_dashboard():
    if "patient_id" not in session: return redirect(url_for("home"))
    conn = get_db(); pid = session["patient_id"]
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    reminders = conn.execute("SELECT * FROM reminders WHERE patient_id=? AND active=1 ORDER BY time_of_day", (pid,)).fetchall()
    sessions = conn.execute("SELECT * FROM game_sessions WHERE patient_id=? ORDER BY played_at DESC LIMIT 30", (pid,)).fetchall()
    difficulties = {r["game_type"]: r["level"] for r in conn.execute("SELECT game_type, level FROM difficulty WHERE patient_id=?", (pid,)).fetchall()}
    today_count = conn.execute("SELECT COUNT(*) FROM game_sessions WHERE patient_id=? AND date(played_at)=date('now')", (pid,)).fetchone()[0]
    total_games = conn.execute("SELECT COUNT(*) FROM game_sessions WHERE patient_id=?", (pid,)).fetchone()[0]
    conn.close()
    recent_acc = round(statistics.mean([s["accuracy"] for s in sessions]), 2) if sessions else 0
    lang = LANGUAGES.get(patient["language"], LANGUAGES["en"])
    return render_template("patient_dashboard.html", patient=patient, reminders=reminders, lang=lang, all_langs=list(LANGUAGES.keys()), difficulties=difficulties, today_count=today_count, total_games=total_games, recent_acc=recent_acc)


@app.route("/patient/set_language", methods=["POST"])
def set_language():
    if "patient_id" not in session: return jsonify({"ok": False}), 403
    lang = request.json.get("language", "en")
    if lang not in LANGUAGES: return jsonify({"ok": False}), 400
    conn = get_db(); conn.execute("UPDATE patients SET language=? WHERE id=?", (lang, session["patient_id"])); conn.commit(); conn.close()
    return jsonify({"ok": True})


@app.route("/patient/mood", methods=["POST"])
def log_mood():
    if "patient_id" not in session: return jsonify({"ok": False}), 403
    mood = request.json.get("mood", "neutral")
    conn = get_db(); conn.execute("INSERT INTO mood_logs (patient_id, mood) VALUES (?,?)", (session["patient_id"], mood)); conn.commit(); conn.close()
    return jsonify({"ok": True})


@app.route("/patient/profile", methods=["POST"])
def update_patient_profile():
    if "patient_id" not in session: return jsonify({"ok": False}), 403
    d = request.json or {}; name = d.get("name", "").strip()
    if len(name) < 2: return jsonify({"ok": False, "error": "Name is too short"}), 400
    conn = get_db(); clash = conn.execute("SELECT id FROM patients WHERE lower(name)=lower(?) AND id<>?", (name, session["patient_id"])).fetchone()
    if clash: conn.close(); return jsonify({"ok": False, "error": "That name is already in use."}), 400
    conn.execute("UPDATE patients SET name=?, language=?, avatar=? WHERE id=?", (name, d.get("language", "en"), d.get("avatar", "👤"), session["patient_id"])); conn.commit(); conn.close()
    return jsonify({"ok": True})


@app.route("/game/<game_type>")
def game(game_type):
    if "patient_id" not in session or game_type not in ("memory", "attention", "routine", "orientation", "language", "visual", "numbers"): return redirect(url_for("patient_dashboard"))
    conn = get_db(); patient = conn.execute("SELECT * FROM patients WHERE id=?", (session["patient_id"],)).fetchone(); diff = conn.execute("SELECT level FROM difficulty WHERE patient_id=? AND game_type=?", (patient["id"], game_type)).fetchone(); conn.close()
    level = diff["level"] if diff else 1
    return render_template(f"game_{game_type}.html", patient=patient, level=level, lang=LANGUAGES.get(patient["language"], LANGUAGES["en"]))


@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    if "patient_id" not in session: return jsonify({"ok": False}), 403
    data = request.json or {}; game_type = data.get("game_type")
    if game_type not in ("memory", "attention", "routine", "orientation", "language", "visual", "numbers"): return jsonify({"ok": False}), 400
    accuracy = max(0, min(1, float(data.get("accuracy", 0)))); avg_time_ms = max(0, int(data.get("avg_time_ms", 4000))); score = int(data.get("score", accuracy * 100)); level_played = int(data.get("level", 1)); pid = session["patient_id"]
    conn = get_db(); conn.execute("INSERT INTO game_sessions (patient_id, game_type, level, accuracy, avg_time_ms, score) VALUES (?,?,?,?,?,?)", (pid, game_type, level_played, accuracy, avg_time_ms, score)); conn.commit(); conn.close()
    new_level, rolling_acc, reason = update_difficulty(pid, game_type, accuracy, avg_time_ms)
    return jsonify({"ok": True, "new_level": new_level, "rolling_accuracy": rolling_acc, "reason": reason})


@app.route("/api/reminder/<int:reminder_id>/complete", methods=["POST"])
def complete_reminder(reminder_id):
    if "patient_id" not in session: return jsonify({"ok": False}), 403
    conn = get_db(); own = conn.execute("SELECT 1 FROM reminders WHERE id=? AND patient_id=?", (reminder_id, session["patient_id"])).fetchone()
    if own: conn.execute("INSERT INTO reminder_logs (reminder_id) VALUES (?)", (reminder_id,)); conn.commit()
    conn.close(); return jsonify({"ok": bool(own)})


@app.route("/caregiver/dashboard")
def caregiver_dashboard():
    if "caregiver_id" not in session: return redirect(url_for("home"))
    conn = get_db(); cg = conn.execute("SELECT * FROM caregivers WHERE id=?", (session["caregiver_id"],)).fetchone()
    patients = conn.execute("SELECT p.* FROM patients p JOIN patient_caregiver pc ON pc.patient_id=p.id WHERE pc.caregiver_id=? ORDER BY p.name", (cg["id"],)).fetchall()
    summaries=[]
    for p in patients:
        ss=conn.execute("SELECT * FROM game_sessions WHERE patient_id=? AND played_at>=datetime('now','-7 day') ORDER BY played_at", (p["id"],)).fetchall(); avg=round(statistics.mean([s["accuracy"] for s in ss]),2) if ss else None
        active=conn.execute("SELECT * FROM reminders WHERE patient_id=? AND active=1", (p["id"],)).fetchall(); missed=[]
        for r in active:
            if not conn.execute("SELECT 1 FROM reminder_logs WHERE reminder_id=? AND date(completed_at)=date('now')", (r["id"],)).fetchone(): missed.append(r)
        alert = "Performance needs a closer look" if avg is not None and avg<.5 else ("No game activity this week" if not ss else None)
        summaries.append({"patient":p,"sessions_count":len(ss),"avg_accuracy":avg,"missed_reminders":missed,"alert":alert})
    conn.close(); return render_template("caregiver_dashboard.html", caregiver=cg, summaries=summaries)


@app.route("/caregiver/patient/add", methods=["POST"])
def caregiver_add_patient():
    if "caregiver_id" not in session: return jsonify({"ok":False}),403
    d=request.json or {}; name=d.get("name","").strip()
    if len(name)<2: return jsonify({"ok":False,"error":"Enter a patient name."}),400
    conn=get_db(); exists=conn.execute("SELECT id FROM patients WHERE lower(name)=lower(?)",(name,)).fetchone()
    if exists: conn.close(); return jsonify({"ok":False,"error":"A patient with that name already exists."}),400
    c=conn.cursor(); c.execute("INSERT INTO patients (name,language,avatar,notes) VALUES (?,?,?,?)",(name,d.get("language","en"),d.get("avatar","👤"),d.get("notes",""))); pid=c.lastrowid
    for g in ("memory","attention","routine","orientation","language","visual","numbers"): c.execute("INSERT OR IGNORE INTO difficulty VALUES (?,?,1)",(pid,g))
    c.execute("INSERT INTO patient_caregiver VALUES (?,?)",(pid,session["caregiver_id"])); conn.commit(); conn.close(); return jsonify({"ok":True,"patient_id":pid})


@app.route("/caregiver/patient/<int:patient_id>/edit", methods=["POST"])
def caregiver_edit_patient(patient_id):
    if "caregiver_id" not in session or not ensure_patient_access(patient_id, session["caregiver_id"]): return jsonify({"ok":False}),403
    d=request.json or {}; name=d.get("name","").strip()
    if len(name)<2: return jsonify({"ok":False,"error":"Enter a patient name."}),400
    conn=get_db(); clash=conn.execute("SELECT id FROM patients WHERE lower(name)=lower(?) AND id<>?",(name,patient_id)).fetchone()
    if clash: conn.close(); return jsonify({"ok":False,"error":"Another patient already has that name."}),400
    conn.execute("UPDATE patients SET name=?,language=?,avatar=?,notes=? WHERE id=?",(name,d.get("language","en"),d.get("avatar","👤"),d.get("notes",""),patient_id)); conn.commit(); conn.close(); return jsonify({"ok":True})


@app.route("/caregiver/patient/<int:patient_id>/difficulty", methods=["POST"])
def caregiver_difficulty(patient_id):
    if "caregiver_id" not in session or not ensure_patient_access(patient_id, session["caregiver_id"]): return jsonify({"ok":False}),403
    d=request.json or {}; game=d.get("game_type"); level=max(1,min(5,int(d.get("level",1))))
    if game not in ("memory","attention","routine","orientation","language","visual","numbers"): return jsonify({"ok":False}),400
    conn=get_db(); conn.execute("INSERT INTO difficulty VALUES (?,?,?) ON CONFLICT(patient_id,game_type) DO UPDATE SET level=excluded.level",(patient_id,game,level)); conn.commit(); conn.close(); return jsonify({"ok":True})


@app.route("/caregiver/patient/<int:patient_id>")
def caregiver_patient_detail(patient_id):
    if "caregiver_id" not in session or not ensure_patient_access(patient_id, session["caregiver_id"]): return redirect(url_for("caregiver_dashboard"))
    conn=get_db(); patient=conn.execute("SELECT * FROM patients WHERE id=?",(patient_id,)).fetchone(); sessions=conn.execute("SELECT * FROM game_sessions WHERE patient_id=? ORDER BY played_at DESC LIMIT 30",(patient_id,)).fetchall(); reminders=conn.execute("SELECT * FROM reminders WHERE patient_id=? ORDER BY time_of_day",(patient_id,)).fetchall(); moods=conn.execute("SELECT * FROM mood_logs WHERE patient_id=? ORDER BY logged_at DESC LIMIT 10",(patient_id,)).fetchall(); diffs=conn.execute("SELECT game_type,level FROM difficulty WHERE patient_id=?",(patient_id,)).fetchall(); conn.close()
    chart_data={"labels":[],"accuracy":[]}
    for s in reversed(sessions): chart_data["labels"].append(s["played_at"][5:16]); chart_data["accuracy"].append(round(s["accuracy"]*100,1))
    difficulty={d["game_type"]:d["level"] for d in diffs}
    return render_template("patient_detail.html",patient=patient,sessions=sessions,reminders=reminders,moods=moods,chart_data=chart_data,difficulty=difficulty)


@app.route("/caregiver/reminder/add", methods=["POST"])
def add_reminder():
    if "caregiver_id" not in session: return jsonify({"ok":False}),403
    d=request.json or {}; pid=int(d["patient_id"])
    if not ensure_patient_access(pid,session["caregiver_id"]): return jsonify({"ok":False}),403
    conn=get_db(); conn.execute("INSERT INTO reminders (patient_id,category,title,time_of_day,recurring) VALUES (?,?,?,?,?)",(pid,d["category"],d["title"],d["time_of_day"],d.get("recurring","daily"))); conn.commit(); conn.close(); return jsonify({"ok":True})


@app.route("/caregiver/reminder/<int:reminder_id>/toggle", methods=["POST"])
def toggle_reminder(reminder_id):
    if "caregiver_id" not in session: return jsonify({"ok":False}),403
    conn=get_db(); r=conn.execute("SELECT r.active FROM reminders r JOIN patient_caregiver pc ON pc.patient_id=r.patient_id WHERE r.id=? AND pc.caregiver_id=?",(reminder_id,session["caregiver_id"])).fetchone()
    if not r: conn.close(); return jsonify({"ok":False}),403
    conn.execute("UPDATE reminders SET active=? WHERE id=?",(0 if r["active"] else 1,reminder_id)); conn.commit(); conn.close(); return jsonify({"ok":True})


if __name__ == "__main__":
    init_db(); app.run(host="0.0.0.0",port=5000,debug=True)
