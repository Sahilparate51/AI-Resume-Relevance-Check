import sqlite3

DATABASE_NAME = "resume_evaluations.db"

def create_table():
    """Creates the database table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY,
            jd_title TEXT,
            resume_filename TEXT,
            relevance_score REAL,
            verdict TEXT,
            missing_skills TEXT,
            feedback TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_evaluation(jd_title, resume_filename, score, verdict, missing_skills, feedback):
    """Inserts a new evaluation record into the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO evaluations (jd_title, resume_filename, relevance_score, verdict, missing_skills, feedback)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (jd_title, resume_filename, score, verdict, missing_skills, feedback))
    conn.commit()
    conn.close()

def fetch_all_evaluations():
    """Retrieves all evaluation records."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()
    return records