from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, send_from_directory
from database import get_db
from helpers import login_required, get_current_user, get_avatar_initials
import os
import werkzeug.utils

hr_documents_bp = Blueprint('hr_documents', __name__, url_prefix='/hr/documents')

@hr_documents_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    db = get_db(current_app)
    user = get_current_user()
    initials = get_avatar_initials(user['name']) if user else 'U'
    
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
    os.makedirs(upload_dir, exist_ok=True)
    
    if request.method == 'POST':
        title = request.form.get('title')
        if 'document' in request.files and title:
            file = request.files['document']
            if file.filename:
                filename = werkzeug.utils.secure_filename(file.filename)
                file.save(os.path.join(upload_dir, filename))
                db.execute('INSERT INTO documents (user_id, title, file_name) VALUES (?, ?, ?)',
                           (session['user_id'], title, filename))
                db.commit()
                return redirect(url_for('hr_documents.index'))

    documents = db.execute('''
        SELECT d.*, u.name as uploader_name 
        FROM documents d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.created_at DESC
    ''').fetchall()

    return render_template('hr/documents.html',
        user=user,
        initials=initials,
        documents=documents
    )

@hr_documents_bp.route('/download/<filename>')
@login_required
def download(filename):
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
    return send_from_directory(upload_dir, werkzeug.utils.secure_filename(filename), as_attachment=True)
