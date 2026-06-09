from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import get_db
from flask import current_app
import json
import os

public_bp = Blueprint('public', __name__)

@public_bp.route('/f/<slug>', methods=['GET', 'POST'])
def submit(slug):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE slug = ? AND is_published = 1', (slug,)).fetchone()
    
    if not form:
        return render_template('public/not_found.html'), 404
    
    questions = db.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index', (form['id'],)
    ).fetchall()
    
    questions_data = []
    for q in questions:
        q_dict = dict(q)
        try:
            q_dict['options'] = json.loads(q_dict.get('options') or '[]')
        except Exception:
            q_dict['options'] = []
        try:
            q_dict['logic_rules'] = json.loads(q_dict.get('logic_rules') or '[]')
        except Exception:
            q_dict['logic_rules'] = []
        questions_data.append(q_dict)
    
    if request.method == 'POST':
        respondent_ip = request.remote_addr or ''
        submitted_key = f'form_submitted_{form["id"]}'

        if not form['allow_multiple_responses']:
            existing_response = db.execute(
                'SELECT id FROM responses WHERE form_id = ? AND respondent_ip = ? LIMIT 1',
                (form['id'], respondent_ip)
            ).fetchone()
            if session.get(submitted_key) or existing_response:
                flash('A response has already been submitted for this form.', 'info')
                return render_template('public/success.html', form=form)
        
        # Create response record
        db.execute(
            'INSERT INTO responses (form_id, respondent_ip) VALUES (?, ?)',
            (form['id'], respondent_ip)
        )
        db.commit()
        
        response_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Process answers
        for q in questions_data:
            q_id = q['id']
            q_type = q['question_type']
            
            if q_type == 'file_upload':
                file = request.files.get(f'q_{q_id}')
                if file and file.filename:
                    import werkzeug.utils
                    filename = werkzeug.utils.secure_filename(file.filename)
                    import secrets
                    unique_name = secrets.token_hex(8) + '_' + filename
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
                    file.save(filepath)
                    answer_value = unique_name
                else:
                    answer_value = ''
            elif q_type == 'checkboxes':
                values = request.form.getlist(f'q_{q_id}')
                answer_value = ', '.join(values)
            else:
                answer_value = request.form.get(f'q_{q_id}', '').strip()
            
            # Validate required
            if q['is_required'] and not answer_value:
                db.execute('DELETE FROM responses WHERE id = ?', (response_id,))
                db.commit()
                flash(f'Please answer the required question: {q["question_text"]}', 'error')
                return render_template('public/form.html', form=form, questions=questions_data)
            
            db.execute(
                'INSERT INTO answers (response_id, question_id, answer_value) VALUES (?, ?, ?)',
                (response_id, q_id, answer_value)
            )
        
        db.commit()
        session[submitted_key] = True
        return render_template('public/success.html', form=form)
    
    return render_template('public/form.html', form=form, questions=questions_data)
