from flask_login import UserMixin

from .database import get_db


class User(UserMixin):
    """Small user model backed by SQLite."""

    def __init__(
        self,
        user_id,
        name,
        email,
        password_hash,
        is_premium,
        created_at,
        is_admin=False,
    ):
        self.id = user_id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.is_premium = bool(is_premium)
        self.created_at = created_at
        self.is_admin = bool(is_admin)

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            user_id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_premium=row["is_premium"],
            created_at=row["created_at"],
            is_admin=row["is_admin"] if "is_admin" in row.keys() else 0,
        )

    @classmethod
    def get_by_id(cls, user_id):
        row = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return cls.from_row(row)

    @classmethod
    def get_by_email(cls, email):
        row = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return cls.from_row(row)

    @classmethod
    def create(cls, name, email, password_hash, is_admin=False):
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO users (name, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password_hash, int(is_admin)),
        )
        db.commit()
        return cls.get_by_id(cursor.lastrowid)
