import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager

from .database import init_app
from .models import User


login_manager = LoginManager()


def create_app(test_config=None):
    """Create and configure the IELTS Platform Flask application."""
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-secret"),
        DATABASE=os.getenv(
            "DATABASE_PATH",
            str(Path(app.instance_path) / "ielts_platform.sqlite3"),
        ),
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database_parent = Path(app.config["DATABASE"]).parent
    if str(database_parent) not in {"", "."}:
        database_parent.mkdir(parents=True, exist_ok=True)

    init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access that page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    from .auth import auth_bp
    from .main import main_bp
    from .mocks import mocks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(mocks_bp)

    return app
