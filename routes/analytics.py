from flask import Blueprint, render_template, session, jsonify
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials
from flask import current_app
import json

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
@login_required
def index():
    db = get_db(current_app)
    user_id = session['user_id']
    
    # Response trend last 30 days
    trend_data = db.execute('''
        SELECT DATE(r.submitted_at) as day, COUNT(*) as count
        FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ? AND r.submitted_at >= DATE('now', '-30 days')
        GROUP BY DATE(r.submitted_at)
        ORDER BY day ASC
    ''', (user_id,)).fetchall()
    
    # Form popularity
    form_popularity = db.execute('''
        SELECT f.title, COUNT(r.id) as response_count
        FROM forms f
        LEFT JOIN responses r ON f.id = r.form_id
        WHERE f.user_id = ?
        GROUP BY f.id
        ORDER BY response_count DESC
        LIMIT 8
    ''', (user_id,)).fetchall()
    
    # Responses by hour of day
    hourly_data = db.execute('''
        SELECT CAST(strftime('%H', r.submitted_at) AS INTEGER) as hour, COUNT(*) as count
        FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ?
        GROUP BY hour
        ORDER BY hour
    ''', (user_id,)).fetchall()
    
    # Weekly breakdown
    weekly_data = db.execute('''
        SELECT strftime('%w', r.submitted_at) as dow, COUNT(*) as count
        FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ? AND r.submitted_at >= DATE('now', '-90 days')
        GROUP BY dow
    ''', (user_id,)).fetchall()
    
    # Stats
    total_forms = db.execute('SELECT COUNT(*) FROM forms WHERE user_id = ?', (user_id,)).fetchone()[0]
    published_forms = db.execute('SELECT COUNT(*) FROM forms WHERE user_id = ? AND is_published = 1', (user_id,)).fetchone()[0]
    total_responses = db.execute('''
        SELECT COUNT(*) FROM responses r
        JOIN forms f ON r.form_id = f.id WHERE f.user_id = ?
    ''', (user_id,)).fetchone()[0]
    
    ai_reports = db.execute('SELECT COUNT(*) FROM ai_reports WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    return render_template('analytics/index.html',
        user=user, initials=initials,
        trend_data=[dict(r) for r in trend_data],
        form_popularity=[dict(r) for r in form_popularity],
        hourly_data=[dict(r) for r in hourly_data],
        weekly_data=[dict(r) for r in weekly_data],
        total_forms=total_forms,
        published_forms=published_forms,
        total_responses=total_responses,
        ai_reports=ai_reports
    )
