from flask import Flask, abort
from database import init_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.forms import forms_bp
from routes.responses import responses_bp
from routes.analytics import analytics_bp
from routes.settings import settings_bp
from routes.public import public_bp
from routes.api import api_bp
import os
import secrets

# Load .env file manually (no external dependency needed)
def _load_env_file(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key and key not in os.environ:
                        os.environ[key] = value
    except FileNotFoundError:
        pass

_load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload
    app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'instance', 'smartforms.db')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

    with app.app_context():
        init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(forms_bp)
    app.register_blueprint(responses_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp)

    return app

app = create_app()

# ── Debug route: visit http://localhost:5000/debug/test-groq in your browser ──
@app.route('/debug/test-groq')
def debug_test_groq():
    import urllib.request, urllib.error, json
    if os.environ.get('ENABLE_DEBUG_ROUTES') != '1':
        abort(404)

    results = []

    # 1. Check .env loading
    api_key = os.environ.get('GROQ_API_KEY', '')
    if api_key:
        results.append(f"✅ GROQ_API_KEY loaded from .env: {api_key[:8]}...{api_key[-4:]}")
    else:
        results.append("❌ GROQ_API_KEY is EMPTY — .env was not loaded or key is missing")
        return '<br>'.join(results)

    # 2. Test: list models
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={'Authorization': f'Bearer {api_key}'},
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            models = sorted([m['id'] for m in data.get('data', [])])
            results.append(f"✅ API key is VALID — {len(models)} models available")
            results.append("Models: " + ", ".join(models[:15]))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        results.append(f"❌ List models failed — HTTP {e.code}: {body[:300]}")
        return '<br>'.join(results)

    # 3. Test: chat completion with llama-3.1-8b-instant
    try:
        payload = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "Say hello in one word."}],
            "max_tokens": 10
        }).encode()
        req2 = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req2, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            reply = data['choices'][0]['message']['content']
            results.append(f"✅ Chat completion works! Model replied: '{reply}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        results.append(f"❌ Chat completion failed — HTTP {e.code}: {body[:300]}")

    results.append("<br>🎉 If all checks passed, restart Flask (Ctrl+C then python app.py) and try AI features again.")
    return '<br>'.join(results)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG') == '1'
    app.run(debug=debug, host='0.0.0.0', port=5000)
