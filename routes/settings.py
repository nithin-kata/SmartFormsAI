from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials, hash_password, verify_password
from flask import current_app
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def index():
    db = get_db(current_app)
    user = get_current_user()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'profile':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            
            if not name or len(name) < 2:
                flash('Name must be at least 2 characters.', 'error')
            elif not email or '@' not in email:
                flash('Valid email required.', 'error')
            else:
                existing = db.execute('SELECT id FROM users WHERE email = ? AND id != ?',
                                      (email, session['user_id'])).fetchone()
                if existing:
                    flash('Email already in use.', 'error')
                else:
                    db.execute('UPDATE users SET name = ?, email = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                               (name, email, session['user_id']))
                    db.commit()
                    session['user_name'] = name
                    session['user_email'] = email
                    flash('Profile updated successfully.', 'success')
        
        elif action == 'password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            
            if not verify_password(current_pw, user['password_hash']):
                flash('Current password is incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'error')
            elif new_pw != confirm_pw:
                flash('Passwords do not match.', 'error')
            else:
                new_hash = hash_password(new_pw)
                db.execute('UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                           (new_hash, session['user_id']))
                db.commit()
                flash('Password changed successfully.', 'success')
        
        elif action == 'api_key':
            groq_key = request.form.get('groq_api_key', '').strip()
            db.execute('UPDATE users SET groq_api_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                       (groq_key, session['user_id']))
            db.commit()
            flash('API key saved successfully.', 'success')
        
        return redirect(url_for('settings.index'))
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    env_gemini_key = bool(os.environ.get('GEMINI_API_KEY', ''))
    user_has_key = bool((user['groq_api_key'] or '').strip()) if user else False
    # Determine AI status label
    if user_has_key or env_gemini_key:
        ai_status = 'gemini'
    else:
        ai_status = 'template'
    return render_template('settings/index.html', user=user, initials=initials,
                           env_gemini_key=env_gemini_key, ai_status=ai_status)
