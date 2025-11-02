from sqlmodel import create_engine, Session, SQLModel
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./truthpod.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def init_db():
    """Initialize database schema.

    - In production, prefer running Alembic migrations.
    - For local dev/tests, you can set TRUTHPOD_RESET_DB=1 to drop and recreate tables.
    - Otherwise, this will create any missing tables without dropping existing ones.
    """
    reset = os.getenv("TRUTHPOD_RESET_DB", "").lower() in ("1", "true", "yes")
    if reset:
        try:
            SQLModel.metadata.drop_all(engine)
        except Exception:
            pass
    # Create any missing tables (safe in prod when migrations are also used)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
