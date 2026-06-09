import sqlite3
import os
from flask import g

def get_db(app=None):
    from flask import current_app
    if app is None:
        app = current_app
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar_color TEXT DEFAULT '#6366f1',
                groq_api_key TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                slug TEXT UNIQUE NOT NULL,
                is_published INTEGER DEFAULT 0,
                allow_multiple_responses INTEGER DEFAULT 1,
                show_progress_bar INTEGER DEFAULT 1,
                success_message TEXT DEFAULT 'Thank you for your response!',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                is_required INTEGER DEFAULT 0,
                options TEXT DEFAULT '[]',
                placeholder TEXT DEFAULT '',
                order_index INTEGER DEFAULT 0,
                logic_rules TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER NOT NULL,
                respondent_email TEXT DEFAULT '',
                respondent_ip TEXT DEFAULT '',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completion_time INTEGER DEFAULT 0,
                FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_value TEXT DEFAULT '',
                FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                report_type TEXT DEFAULT 'analysis',
                content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                file_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT DEFAULT '',
                manager_id INTEGER,
                FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL
            );
        ''')
        
        # Self-healing migration to add logic_rules column to questions table if it doesn't exist
        try:
            db.execute("ALTER TABLE questions ADD COLUMN logic_rules TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        db.commit()
        db.close()

    app.teardown_appcontext(close_db)
