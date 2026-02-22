from sqlalchemy import create_engine, Column, String, Boolean, text
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
    # Comma-separated league codes (e.g. "epl,ucl,champ"). Empty/None means ALL.
    leagues = Column(String, default="")


def _ensure_schema():
    """
    Adds the 'leagues' column if your users.db was created before this upgrade.
    Safe to run on every startup.
    """
    with engine.connect() as conn:
        try:
            rows = conn.execute(text("PRAGMA table_info(users);")).fetchall()
            existing_cols = {r[1] for r in rows}  # r[1] = column name
            if "leagues" not in existing_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN leagues VARCHAR DEFAULT ''"))
        except Exception:
            # If table doesn't exist yet, create_all will handle it
            pass


_ensure_schema()
Base.metadata.create_all(bind=engine)
