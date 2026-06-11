from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from database import get_db
from helpers import login_required, employee_required, get_current_user, get_avatar_initials

hr_announcements_bp = Blueprint('hr_announcements', __name__, url_prefix='/hr/announcements')

@hr_announcements_bp.route('/', methods=['GET', 'POST'])
@employee_required
def index():
    db = get_db(current_app)
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title:
            flash('Announcement title is required.', 'error')
        elif not content:
            flash('Announcement content is required.', 'error')
        else:
            try:
                db.execute('INSERT INTO announcements (user_id, title, content) VALUES (?, ?, ?)',
                           (session['user_id'], title, content))
                db.commit()
                flash('Announcement posted successfully.', 'success')
                return redirect(url_for('hr_announcements.index'))
            except Exception as e:
                flash(f'Error posting announcement: {str(e)}', 'error')

    announcements = db.execute('''
        SELECT a.*, datetime(a.created_at, 'localtime') as local_created_at, u.name as author_name 
        FROM announcements a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    ''').fetchall()

    return render_template('hr/announcements.html',
        user=user,
        initials=initials,
        announcements=announcements
    )
