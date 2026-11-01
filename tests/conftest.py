import pytest

from app import create_app
from app.database import init_db


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.sqlite3"),
        }
    )
    with app.app_context():
        init_db()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()

# Simulate the CSRF header a rendered browser form or AI client sends. Tests
# exercising missing/invalid tokens deliberately use FlaskClient directly.
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers
import secrets


class BrowserClient(FlaskClient):
    def open(self, *args, **kwargs):
        path = str(args[0]) if args else kwargs.get('path', '')
        method = kwargs.get('method', 'GET').upper()
        if method in ('POST','PUT','PATCH','DELETE') and path.startswith(('/auth/','/mocks/','/ai/')):
            headers = Headers(kwargs.get('headers'))
            data = kwargs.get('data')
            explicit_form_token = hasattr(data, 'get') and data.get('csrf_token') is not None
            if not explicit_form_token and 'X-CSRF-Token' not in headers:
                with self.session_transaction() as session:
                    token = session.setdefault('app_csrf_token', secrets.token_urlsafe(32))
                headers['X-CSRF-Token'] = token
                kwargs['headers'] = headers
        return super().open(*args, **kwargs)


@pytest.fixture(autouse=True)
def browser_csrf_defaults(app, monkeypatch):
    monkeypatch.setattr(app, 'test_client_class', BrowserClient)
