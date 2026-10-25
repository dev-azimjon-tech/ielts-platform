import sqlite3

import click
from flask import current_app, g


def get_db():
    """Return the current request's SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        schema = schema_file.read()
        if isinstance(schema, bytes):
            schema = schema.decode("utf-8")
        db.executescript(schema)

    # Keep existing installations working when a new column is introduced.
    user_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
    }
    if "is_admin" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
        )
    db.commit()


@click.command("init-db")
def init_db_command():
    """Create the database tables."""
    init_db()
    click.echo("Initialized the database.")


@click.command("create-admin")
@click.option("--email", prompt=True, help="Email address for the admin account.")
@click.option("--name", prompt=True, help="Name shown in the admin panel.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for the admin account.",
)
def create_admin_command(email, name, password):
    """Create an admin account or promote an existing account."""
    from werkzeug.security import generate_password_hash

    from .models import User

    email = email.strip().lower()
    name = name.strip()
    if not email or not name:
        raise click.ClickException("Name and email are required.")
    if len(password) < 8:
        raise click.ClickException("The password must be at least 8 characters.")

    init_db()
    existing_user = User.get_by_email(email)
    db = get_db()
    if existing_user is None:
        User.create(name, email, generate_password_hash(password), is_admin=True)
        click.echo(f"Created admin account for {email}.")
        return

    db.execute(
        """
        UPDATE users
        SET name = ?, password_hash = ?, is_admin = 1
        WHERE id = ?
        """,
        (name, generate_password_hash(password), existing_user.id),
    )
    db.commit()
    click.echo(f"Promoted {email} to admin and updated the password.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)

    @app.cli.command("seed-content")
    def seed_content_command():
        """Load the Reading, Listening, Speaking, and Writing demo content."""
        from .seed import seed_demo_content

        init_db()
        seed_demo_content()
        click.echo("Seeded the Reading, Listening, Speaking, and Writing demo content.")

    @app.cli.command("seed-ai-content")
    def seed_ai_content_command():
        """Load the AI Speaking and Writing practice mocks."""
        from .ai_seed import seed_ai_content

        init_db()
        seed_ai_content()
        click.echo("Seeded 10 Speaking and 10 Writing AI practice mocks.")
