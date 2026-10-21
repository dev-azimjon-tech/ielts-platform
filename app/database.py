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
    db.commit()


@click.command("init-db")
def init_db_command():
    """Create the database tables."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    @app.cli.command("seed-content")
    def seed_content_command():
        """Load the original demo Reading and Listening mocks."""
        from .seed import seed_demo_content

        init_db()
        seed_demo_content()
        click.echo("Seeded the original Reading and Listening demo mocks.")
