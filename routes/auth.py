from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db
from helpers import hash_password, verify_password, get_current_user
from flask import current_app
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
        
        db = get_db(current_app)
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and verify_password(password, user['password_hash']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        invite_code = request.form.get('invite_code', '').strip()
        
        errors = []
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Valid email address is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', name=name, email=email)
        
        db = get_db(current_app)
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('An account with this email already exists.', 'error')
            return render_template('auth/register.html', name=name, email=email)
        
        import random
        colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444']
        avatar_color = random.choice(colors)
        
        password_hash = hash_password(password)
        is_employee = 1 if invite_code and invite_code == os.environ.get('EMPLOYEE_INVITE_CODE') else 0
        db.execute(
            'INSERT INTO users (name, email, password_hash, avatar_color, is_employee) VALUES (?, ?, ?, ?, ?)',
            (name, email, password_hash, avatar_color, is_employee)
        )
        db.commit()
        
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        
        flash(f'Welcome to SmartForms AI, {name}!', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/hr/join', methods=['GET', 'POST'])
def hr_join():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.login'))
        
    db = get_db(current_app)
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user and user['is_employee']:
        flash('You are already an employee.', 'info')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        import os
        invite_code = request.form.get('invite_code', '').strip()
        if invite_code == os.environ.get('EMPLOYEE_INVITE_CODE'):
            db.execute('UPDATE users SET is_employee = 1 WHERE id = ?', (session['user_id'],))
            db.commit()
            flash('Success! You now have access to the HR module.', 'success')
            return redirect(url_for('hr_announcements.index'))
        else:
            flash('Invalid invite code.', 'error')
            
    return render_template('auth/hr_join.html')

