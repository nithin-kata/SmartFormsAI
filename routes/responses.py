from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials
from ai_service import analyze_responses
from flask import current_app
import json
import csv
import io
import os

responses_bp = Blueprint('responses', __name__)

@responses_bp.route('/forms/<int:form_id>/responses')
@login_required
def index(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    questions = db.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index', (form_id,)
    ).fetchall()
    
    search = request.args.get('search', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    per_page = 20
    offset = (page - 1) * per_page
    
    total_responses = db.execute('SELECT COUNT(*) FROM responses WHERE form_id = ?', (form_id,)).fetchone()[0]
    
    responses = db.execute('''
        SELECT * FROM responses WHERE form_id = ?
        ORDER BY submitted_at DESC LIMIT ? OFFSET ?
    ''', (form_id, per_page, offset)).fetchall()
    
    # Get answers for each response
    responses_with_answers = []
    for resp in responses:
        answers = db.execute(
            'SELECT a.*, q.question_text, q.question_type FROM answers a JOIN questions q ON a.question_id = q.id WHERE a.response_id = ?',
            (resp['id'],)
        ).fetchall()
        responses_with_answers.append({
            'response': dict(resp),
            'answers': [dict(a) for a in answers]
        })
    
    total_pages = (total_responses + per_page - 1) // per_page

    # ── Per-question statistics (calculated individually for THIS form only) ──
    question_stats = []
    if total_responses > 0:
        from collections import Counter
        for q in questions:
            q_id = q['id']
            qtype = q['question_type']

            # Fetch ALL answers for this question across this form's responses
            all_answers = db.execute('''
                SELECT a.answer_value
                FROM answers a
                JOIN responses r ON a.response_id = r.id
                WHERE a.question_id = ? AND r.form_id = ? AND a.answer_value != ''
            ''', (q_id, form_id)).fetchall()

            values = [row['answer_value'] for row in all_answers]
            answered = len(values)
            response_rate = round(answered / total_responses * 100) if total_responses else 0

            stat = {
                'question_id': q_id,
                'question_text': q['question_text'],
                'question_type': qtype,
                'answered': answered,
                'total': total_responses,
                'response_rate': response_rate,
            }

            if qtype == 'rating' and values:
                nums = []
                for v in values:
                    try:
                        nums.append(float(v))
                    except ValueError:
                        pass
                if nums:
                    stat['avg'] = round(sum(nums) / len(nums), 1)
                    stat['max'] = int(max(nums))
                    stat['min'] = int(min(nums))
                    # Distribution 1-5
                    dist = {str(i): 0 for i in range(1, 6)}
                    for n in nums:
                        key = str(int(n))
                        if key in dist:
                            dist[key] += 1
                    stat['distribution'] = dist

            elif qtype in ('multiple_choice', 'checkboxes', 'dropdown', 'yes_no') and values:
                counts = Counter(values)
                total_v = sum(counts.values())
                stat['distribution'] = {
                    opt: {'count': cnt, 'pct': round(cnt / total_v * 100)}
                    for opt, cnt in counts.most_common()
                }

            question_stats.append(stat)

    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'

    return render_template('responses/index.html',
        user=user, initials=initials,
        form=form, questions=questions,
        responses=responses_with_answers,
        total_responses=total_responses,
        page=page, total_pages=total_pages, search=search,
        question_stats=question_stats
    )

@responses_bp.route('/forms/<int:form_id>/responses/<int:response_id>')
@login_required
def view(form_id, response_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    response = db.execute('SELECT * FROM responses WHERE id = ? AND form_id = ?',
                          (response_id, form_id)).fetchone()
    if not response:
        flash('Response not found.', 'error')
        return redirect(url_for('responses.index', form_id=form_id))
    
    answers = db.execute('''
        SELECT a.*, q.question_text, q.question_type, q.order_index
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.response_id = ?
        ORDER BY q.order_index
    ''', (response_id,)).fetchall()
    
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    return render_template('responses/view.html',
        user=user, initials=initials,
        form=form, response=response, answers=answers
    )

@responses_bp.route('/forms/<int:form_id>/responses/export')
@login_required
def export_csv(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        flash('Form not found.', 'error')
        return redirect(url_for('forms.index'))
    
    questions = db.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index', (form_id,)
    ).fetchall()
    
    responses = db.execute(
        'SELECT * FROM responses WHERE form_id = ? ORDER BY submitted_at DESC', (form_id,)
    ).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    headers = ['Response ID', 'Submitted At', 'IP Address'] + [q['question_text'] for q in questions]
    writer.writerow(headers)
    
    # Data rows
    for resp in responses:
        answers_map = {}
        answers = db.execute(
            'SELECT * FROM answers WHERE response_id = ?', (resp['id'],)
        ).fetchall()
        for ans in answers:
            answers_map[ans['question_id']] = ans['answer_value']
        
        row = [resp['id'], resp['submitted_at'], resp['respondent_ip']]
        for q in questions:
            row.append(answers_map.get(q['id'], ''))
        writer.writerow(row)
    
    output.seek(0)
    filename = f"{form['title'].replace(' ', '_')}_responses.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

@responses_bp.route('/forms/<int:form_id>/responses/<int:response_id>/delete', methods=['POST'])
@login_required
def delete(form_id, response_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    db.execute('DELETE FROM responses WHERE id = ? AND form_id = ?', (response_id, form_id))
    db.commit()
    return jsonify({'success': True})

@responses_bp.route('/api/forms/<int:form_id>/analyze', methods=['POST'])
@login_required
def ai_analyze(form_id):
    db = get_db(current_app)
    form = db.execute('SELECT * FROM forms WHERE id = ? AND user_id = ?',
                      (form_id, session['user_id'])).fetchone()
    if not form:
        return jsonify({'success': False, 'error': 'Form not found'})

    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    # Use user's personal Gemini key, fall back to server .env key, or use template engine (no key needed)
    api_key = (user['groq_api_key'] or '').strip() or os.environ.get('GEMINI_API_KEY', '').strip()

    questions = db.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index', (form_id,)
    ).fetchall()

    responses = db.execute(
        'SELECT * FROM responses WHERE form_id = ? ORDER BY submitted_at DESC LIMIT 100', (form_id,)
    ).fetchall()

    if not responses:
        return jsonify({'success': False, 'error': 'No responses to analyze yet.'})

    responses_data = []
    for resp in responses:
        answers = db.execute('SELECT * FROM answers WHERE response_id = ?', (resp['id'],)).fetchall()
        responses_data.append({
            'id': resp['id'],
            'submitted_at': str(resp['submitted_at']),
            'answers': [dict(a) for a in answers]
        })

    result = analyze_responses(
        api_key,
        form['title'],
        [dict(q) for q in questions],
        responses_data
    )

    if result['success']:
        # Save report
        db.execute(
            'INSERT INTO ai_reports (form_id, user_id, content) VALUES (?, ?, ?)',
            (form_id, session['user_id'], result['content'])
        )
        db.commit()

    return jsonify(result)
