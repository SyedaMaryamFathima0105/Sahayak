import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "care.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed=True):
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL COLLATE NOCASE UNIQUE,
        pin TEXT,
        language TEXT DEFAULT 'en',
        avatar TEXT DEFAULT '👤',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS caregivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        pin TEXT NOT NULL,
        role TEXT DEFAULT 'family'
    );
    CREATE TABLE IF NOT EXISTS patient_caregiver (
        patient_id INTEGER,
        caregiver_id INTEGER,
        UNIQUE(patient_id, caregiver_id),
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(caregiver_id) REFERENCES caregivers(id)
    );
    CREATE TABLE IF NOT EXISTS difficulty (
        patient_id INTEGER,
        game_type TEXT,
        level INTEGER DEFAULT 1,
        PRIMARY KEY (patient_id, game_type),
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    CREATE TABLE IF NOT EXISTS game_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        game_type TEXT,
        level INTEGER,
        accuracy REAL,
        avg_time_ms INTEGER,
        score INTEGER,
        played_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        category TEXT,
        title TEXT,
        time_of_day TEXT,
        recurring TEXT DEFAULT 'daily',
        active INTEGER DEFAULT 1,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    CREATE TABLE IF NOT EXISTS reminder_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reminder_id INTEGER,
        completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(reminder_id) REFERENCES reminders(id)
    );
    CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        mood TEXT,
        logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    """)

    # Gentle migration for the original prototype DB.
    cols = [r[1] for r in c.execute("PRAGMA table_info(patients)").fetchall()]
    if "notes" not in cols:
        c.execute("ALTER TABLE patients ADD COLUMN notes TEXT DEFAULT ''")
    if "last_seen" not in cols:
        c.execute("ALTER TABLE patients ADD COLUMN last_seen TEXT")
    # SQLite cannot easily add a UNIQUE constraint to an existing table, so
    # name matching is handled case-insensitively by application queries.

    if seed and c.execute("SELECT COUNT(*) FROM caregivers").fetchone()[0] == 0:
        c.execute("INSERT INTO caregivers (name, pin, role) VALUES (?,?,?)", ("Dr.Sachin (ASHA worker)", "9999", "health_worker"))
        c.execute("INSERT INTO caregivers (name, pin, role) VALUES (?,?,?)", ("Dhanush (Son)", "5555", "family"))

    if seed and c.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
        patients = [("Ratan Gogoi", "en", "👴"), ("Mema Lyngdoh", "en", "👵")]
        for name, lang, avatar in patients:
            c.execute("INSERT INTO patients (name, language, avatar) VALUES (?,?,?)", (name, lang, avatar))
        c.execute("INSERT OR IGNORE INTO patient_caregiver VALUES (1,1)")
        c.execute("INSERT OR IGNORE INTO patient_caregiver VALUES (1,2)")
        c.execute("INSERT OR IGNORE INTO patient_caregiver VALUES (2,1)")
        for pid in (1, 2):
            for g in ("memory", "attention", "routine", "orientation", "language", "visual", "numbers"):
                c.execute("INSERT OR IGNORE INTO difficulty VALUES (?,?,1)", (pid, g))
        today = datetime.now()
        reminders = [
            (1, "medicine", "Morning medicine", "08:30", "daily"),
            (1, "hydration", "Drink a glass of water", "11:00", "daily"),
            (1, "activity", "Evening walk with family", "17:00", "daily"),
            (1, "appointment", "Follow-up appointment", (today + timedelta(days=3)).strftime("%H:%M"), "once"),
            (2, "medicine", "Morning medicine", "09:00", "daily"),
            (2, "hydration", "Drink water after lunch", "13:30", "daily"),
            (2, "activity", "Music / quiet activity", "16:00", "daily"),
        ]
        c.executemany("INSERT INTO reminders (patient_id, category, title, time_of_day, recurring) VALUES (?,?,?,?,?)", reminders)

        import random
        for pid in (1, 2):
            for i in range(6):
                day = (today - timedelta(days=(6 - i))).strftime("%Y-%m-%d %H:%M:%S")
                acc = round(random.uniform(0.55, 0.95), 2)
                c.execute("INSERT INTO game_sessions (patient_id, game_type, level, accuracy, avg_time_ms, score, played_at) VALUES (?,?,?,?,?,?,?)",
                           (pid, random.choice(["memory", "attention", "routine"]), random.randint(1, 3), acc, random.randint(1500, 6000), int(acc * 100), day))
    # Ensure every existing patient has a starting level for the expanded game library.
    game_types = ("memory", "attention", "routine", "orientation", "language", "visual", "numbers")
    for patient in c.execute("SELECT id FROM patients").fetchall():
        for game_type in game_types:
            c.execute("INSERT OR IGNORE INTO difficulty VALUES (?,?,1)", (patient[0], game_type))

    conn.commit()
    conn.close()
