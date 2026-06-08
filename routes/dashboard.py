from flask import Blueprint, render_template, session
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials
from flask import current_app

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    db = get_db(current_app)
    user_id = session['user_id']
    
    # Stats
    total_forms = db.execute('SELECT COUNT(*) FROM forms WHERE user_id = ?', (user_id,)).fetchone()[0]
    total_responses = db.execute('''
        SELECT COUNT(*) FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ?
    ''', (user_id,)).fetchone()[0]
    ai_reports = db.execute('SELECT COUNT(*) FROM ai_reports WHERE user_id = ?', (user_id,)).fetchone()[0]
    published_forms = db.execute('SELECT COUNT(*) FROM forms WHERE user_id = ? AND is_published = 1', (user_id,)).fetchone()[0]

    # Recent forms with response counts
    recent_forms = db.execute('''
        SELECT f.*,
               COUNT(r.id) as response_count,
               MAX(r.submitted_at) as last_response
        FROM forms f
        LEFT JOIN responses r ON f.id = r.form_id
        WHERE f.user_id = ?
        GROUP BY f.id
        ORDER BY f.updated_at DESC
        LIMIT 5
    ''', (user_id,)).fetchall()

    # Per-form response counts — each form counted separately
    all_forms_with_counts = db.execute('''
        SELECT f.id, f.title, f.is_published, f.slug,
               COUNT(r.id) as response_count
        FROM forms f
        LEFT JOIN responses r ON f.id = r.form_id
        WHERE f.user_id = ?
        GROUP BY f.id
        ORDER BY response_count DESC, f.updated_at DESC
    ''', (user_id,)).fetchall()

    # Recent responses
    recent_responses = db.execute('''
        SELECT r.*, f.title as form_title
        FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ?
        ORDER BY r.submitted_at DESC
        LIMIT 8
    ''', (user_id,)).fetchall()

    # Response trend (last 7 days)
    response_trend = db.execute('''
        SELECT DATE(r.submitted_at) as day, COUNT(*) as count
        FROM responses r
        JOIN forms f ON r.form_id = f.id
        WHERE f.user_id = ? AND r.submitted_at >= DATE('now', '-7 days')
        GROUP BY DATE(r.submitted_at)
        ORDER BY day ASC
    ''', (user_id,)).fetchall()

    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'

    return render_template('dashboard/index.html',
        user=user,
        initials=initials,
        total_forms=total_forms,
        total_responses=total_responses,
        ai_reports=ai_reports,
        published_forms=published_forms,
        recent_forms=recent_forms,
        all_forms_with_counts=[dict(r) for r in all_forms_with_counts],
        recent_responses=recent_responses,
        response_trend=[dict(r) for r in response_trend]
    )
