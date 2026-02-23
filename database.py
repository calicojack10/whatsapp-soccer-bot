# database.py
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    phone = Column(String, primary_key=True, index=True)
    auto_updates = Column(Boolean, default=False)
    leagues = Column(String, default="")  # comma-separated codes


class MessageLog(Base):
    """
    Stores processed WhatsApp message IDs to prevent duplicate replies when Meta retries.
    """
    __tablename__ = "message_log"

    msg_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def _ensure_schema():
    """
    Adds missing columns to existing SQLite DB (safe on every startup).
    """
    with engine.connect() as conn:
        try:
            rows = conn.execute(text("PRAGMA table_info(users);")).fetchall()
            existing_cols = {r[1] for r in rows}
            if "leagues" not in existing_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN leagues VARCHAR DEFAULT ''"))
        except Exception:
            pass


_ensure_schema()
Base.metadata.create_all(bind=engine)
