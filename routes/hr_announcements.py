from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials

hr_announcements_bp = Blueprint('hr_announcements', __name__, url_prefix='/hr/announcements')

@hr_announcements_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    db = get_db(current_app)
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if title and content:
            db.execute('INSERT INTO announcements (user_id, title, content) VALUES (?, ?, ?)',
                       (session['user_id'], title, content))
            db.commit()
            return redirect(url_for('hr_announcements.index'))

    announcements = db.execute('''
        SELECT a.*, u.name as author_name 
        FROM announcements a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    ''').fetchall()

    return render_template('hr/announcements.html',
        user=user,
        initials=initials,
        announcements=announcements
    )
