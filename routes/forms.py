from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials, generate_slug
from ai_service import generate_form_from_prompt
from flask import current_app
import json

forms_bp = Blueprint('forms', __name__)

QUESTION_TYPES = {
    'short_text', 'long_text', 'email', 'phone', 'multiple_choice',
    'checkboxes', 'dropdown', 'rating', 'yes_no', 'date', 'file_upload'
}
OPTION_QUESTION_TYPES = {'multiple_choice', 'checkboxes', 'dropdown'}


def _clean_question_payload(data, existing=None, partial=False):
    data = data or {}
    existing = dict(existing) if existing else {}

    question_text = data.get('question_text', existing.get('question_text', 'Untitled Question'))
    question_text = str(question_text or '').strip()
    if not question_text:
        if partial and existing:
            question_text = existing['question_text']
        else:
            raise ValueError('Question text is required.')

    question_type = data.get('question_type', existing.get('question_type', 'short_text'))
    if question_type not in QUESTION_TYPES:
        raise ValueError('Invalid question type.')

    is_required = 1 if data.get('is_required', existing.get('is_required', 0)) else 0
    placeholder = str(data.get('placeholder', existing.get('placeholder', '')) or '').strip()

    if 'options' in data:
        raw_options = data.get('options') or []
        options_list = [str(option).strip() for option in raw_options if str(option).strip()]
    elif existing:
        try:
            options_list = json.loads(existing['options'] or '[]')
        except Exception:
            options_list = []
    else:
        options_list = []

    if question_type not in OPTION_QUESTION_TYPES:
        options_list = []
    elif not options_list:
        options_list = ['Option 1']

    return question_text, question_type, is_required, json.dumps(options_list), placeholder


def _question_to_dict(question):
    q_dict = dict(question)
    q_dict['question_text'] = str(q_dict.get('question_text') or '').strip() or 'Untitled Question'
    if q_dict.get('question_type') not in QUESTION_TYPES:
        q_dict['question_type'] = 'short_text'
    try:
        q_dict['options'] = json.loads(q_dict['options'] or '[]')
    except Exception:
        q_dict['options'] = []
    if q_dict['question_type'] not in OPTION_QUESTION_TYPES:
        q_dict['options'] = []
    return q_dict

@forms_bp.route('/forms')
@login_required
def index():
    db = get_db(current_app)
    user_id = session['user_id']
    
    search = request.args.get('search', '').strip()
    filter_status = request.args.get('status', 'all')
    
    query = '''
        SELECT f.*, COUNT(r.id) as response_count
        FROM forms f
        LEFT JOIN responses r ON f.id = r.form_id
        WHERE f.user_id = ?
    '''
    params = [user_id]
    
    if search:
        query += ' AND (f.title LIKE ? OR f.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if filter_status == 'published':
        query += ' AND f.is_published = 1'
    elif filter_status == 'draft':
        query += ' AND f.is_published = 0'
    
    query += ' GROUP BY f.id ORDER BY f.updated_at DESC'
    
    forms = db.execute(query, params).fetchall()
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    return render_template('forms/index.html',
        user=user, initials=initials,
        forms=forms, search=search, filter_status=filter_status
    )

@forms_bp.route('/forms/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('Form title is required.', 'error')
            return redirect(url_for('forms.new'))
        
        db = get_db(current_app)
        slug = generate_slug()
        # Ensure unique slug
        while db.execute('SELECT id FROM forms WHERE slug = ?', (slug,)).fetchone():
            slug = generate_slug()
        
        db.execute(
            'INSERT INTO forms (user_id, title, description, slug) VALUES (?, ?, ?, ?)',
            (session['user_id'], title, description, slug)
        )
        db.commit()
        form = db.execute('SELECT * FROM forms WHERE slug = ?', (slug,)).fetchone()
        flash('Form created! Start adding questions.', 'success')
        return redirect(url_for('forms.builder', form_id=form['id']))
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    return render_template('forms/new.html', user=user, initials=initials)

@forms_bp.route('/forms/<int:form_id>/builder')
@login_required
def builder(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?', 
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    questions = db.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index ASC',
        (form_id,)
    ).fetchall()
    
    # Parse options for each question
    questions_data = []
    for q in questions:
        questions_data.append(_question_to_dict(q))
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    return render_template('forms/builder.html',
        user=user, initials=initials,
        form=form, questions=questions_data
    )

@forms_bp.route('/forms/<int:form_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        success_message = request.form.get('success_message', 'Thank you for your response!').strip()
        allow_multiple = 1 if request.form.get('allow_multiple_responses') else 0
        show_progress = 1 if request.form.get('show_progress_bar') else 0

        if not title:
            flash('Form title is required.', 'error')
            user = get_current_user()
            initials = get_avatar_initials(user['name']) if user else 'U'
            return render_template('forms/edit.html', user=user, initials=initials, form=form)
        
        db.execute('''
            UPDATE forms SET title = ?, description = ?, success_message = ?,
            allow_multiple_responses = ?, show_progress_bar = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, description, success_message, allow_multiple, show_progress, form_id))
        db.commit()
        flash('Form settings updated.', 'success')
        return redirect(url_for('forms.builder', form_id=form_id))
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    return render_template('forms/edit.html', user=user, initials=initials, form=form)

@forms_bp.route('/forms/<int:form_id>/publish', methods=['POST'])
@login_required
def publish(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        return jsonify({'success': False, 'error': 'Form not found'})
    
    new_status = 0 if form['is_published'] else 1
    db.execute('UPDATE forms SET is_published = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
               (new_status, form_id))
    db.commit()
    
    status_text = 'published' if new_status else 'unpublished'
    return jsonify({'success': True, 'is_published': new_status, 'message': f'Form {status_text} successfully'})

@forms_bp.route('/forms/<int:form_id>/delete', methods=['POST'])
@login_required
def delete(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    db.execute('DELETE FROM forms WHERE id = ?', (form_id,))
    db.commit()
    flash('Form deleted successfully.', 'success')
    return redirect(url_for('forms.index'))

@forms_bp.route('/forms/<int:form_id>/duplicate', methods=['POST'])
@login_required
def duplicate(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    slug = generate_slug()
    while db.execute('SELECT id FROM forms WHERE slug = ?', (slug,)).fetchone():
        slug = generate_slug()
    
    db.execute('''
        INSERT INTO forms (user_id, title, description, slug, success_message, allow_multiple_responses, show_progress_bar)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], f"Copy of {form['title']}", form['description'],
          slug, form['success_message'], form['allow_multiple_responses'], form['show_progress_bar']))
    db.commit()
    
    new_form = db.execute('SELECT * FROM forms WHERE slug = ?', (slug,)).fetchone()
    
    # Copy questions
    questions = db.execute('SELECT * FROM questions WHERE form_id = ? ORDER BY order_index', (form_id,)).fetchall()
    for q in questions:
        db.execute('''
            INSERT INTO questions (form_id, question_text, question_type, is_required, options, placeholder, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (new_form['id'], q['question_text'], q['question_type'], q['is_required'],
              q['options'], q['placeholder'], q['order_index']))
    db.commit()
    
    flash('Form duplicated successfully.', 'success')
    return redirect(url_for('forms.builder', form_id=new_form['id']))

# Question API endpoints
@forms_bp.route('/api/forms/<int:form_id>/questions', methods=['POST'])
@login_required
def add_question(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        question_text, question_type, is_required, options, placeholder = _clean_question_payload(
            request.get_json() or {}
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    # Get next order index
    max_order = db.execute('SELECT MAX(order_index) FROM questions WHERE form_id = ?', (form_id,)).fetchone()[0]
    order_index = (max_order or 0) + 1
    
    db.execute('''
        INSERT INTO questions (form_id, question_text, question_type, is_required, options, placeholder, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (form_id, question_text, question_type, is_required, options, placeholder, order_index))
    db.commit()
    
    question = db.execute('SELECT * FROM questions WHERE form_id = ? ORDER BY id DESC LIMIT 1', (form_id,)).fetchone()
    q_dict = _question_to_dict(question)
    
    db.execute('UPDATE forms SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (form_id,))
    db.commit()
    
    return jsonify({'success': True, 'question': q_dict})

@forms_bp.route('/api/questions/<int:question_id>', methods=['PUT'])
@login_required
def update_question(question_id):
    db = get_db(current_app)
    question = db.execute('''
        SELECT q.* FROM questions q
        JOIN forms f ON q.form_id = f.id
        WHERE q.id = ? AND f.user_id = ?
    ''', (question_id, session['user_id'])).fetchone()
    
    if not question:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        question_text, question_type, is_required, options, placeholder = _clean_question_payload(
            request.get_json() or {},
            existing=question,
            partial=True
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    db.execute('''
        UPDATE questions SET question_text = ?, question_type = ?, is_required = ?,
        options = ?, placeholder = ? WHERE id = ?
    ''', (question_text, question_type, is_required, options, placeholder, question_id))
    db.execute('UPDATE forms SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (question['form_id'],))
    db.commit()

    updated = db.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    return jsonify({'success': True, 'question': _question_to_dict(updated)})

@forms_bp.route('/api/questions/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    db = get_db(current_app)
    question = db.execute('''
        SELECT q.* FROM questions q
        JOIN forms f ON q.form_id = f.id
        WHERE q.id = ? AND f.user_id = ?
    ''', (question_id, session['user_id'])).fetchone()
    
    if not question:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    db.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    db.execute('UPDATE forms SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (question['form_id'],))
    db.commit()
    
    return jsonify({'success': True})

@forms_bp.route('/api/forms/<int:form_id>/reorder', methods=['POST'])
@login_required
def reorder_questions(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    data = request.get_json()
    order = data.get('order', [])
    
    for index, question_id in enumerate(order):
        db.execute('UPDATE questions SET order_index = ? WHERE id = ? AND form_id = ?',
                   (index, question_id, form_id))
    
    db.execute('UPDATE forms SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (form_id,))
    db.commit()
    
    return jsonify({'success': True})

@forms_bp.route('/api/forms/ai-generate', methods=['POST'])
@login_required
def ai_generate():
    import os
    db = get_db(current_app)
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    # Use user's personal Gemini key, fall back to server .env key, or use template engine (no key needed)
    api_key = (user['groq_api_key'] or '').strip() or os.environ.get('GEMINI_API_KEY', '').strip()

    data = request.get_json()
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'success': False, 'error': 'Please provide a description for your form.'})

    result = generate_form_from_prompt(api_key, prompt)
    return jsonify(result)
