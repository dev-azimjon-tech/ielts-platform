"""CSRF protection for authentication, mock submissions, and AI requests."""
import secrets

from flask import abort, jsonify, request, session

PROTECTED_BLUEPRINTS = {'auth', 'mocks', 'ai'}


def csrf_token():
    if 'app_csrf_token' not in session:
        session['app_csrf_token'] = secrets.token_urlsafe(32)
    return session['app_csrf_token']


def init_app(app):
    @app.context_processor
    def security_context():
        return {'app_csrf_token': csrf_token()}

    @app.before_request
    def protect_requests():
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE') or request.blueprint not in PROTECTED_BLUEPRINTS:
            return
        supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
        expected = session.get('app_csrf_token', '')
        if not expected or not secrets.compare_digest(supplied.encode(), expected.encode()):
            message = 'This form expired. Refresh the page and try again.'
            if request.is_json or request.endpoint in ('ai.speaking_turn', 'ai.complete_speaking'):
                return jsonify(error=message), 400
            abort(400, description=message)
