from flask import Blueprint, jsonify, session
from database import get_db
from helpers import login_required
from flask import current_app

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/stats')
@login_required
def stats():
    db = get_db(current_app)
    user_id = session['user_id']
    
    total_forms = db.execute('SELECT COUNT(*) FROM forms WHERE user_id = ?', (user_id,)).fetchone()[0]
    total_responses = db.execute('''
        SELECT COUNT(*) FROM responses r
        JOIN forms f ON r.form_id = f.id WHERE f.user_id = ?
    ''', (user_id,)).fetchone()[0]
    
    return jsonify({
        'total_forms': total_forms,
        'total_responses': total_responses
    })
