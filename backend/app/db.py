from backend.app.config import settings
from sqlmodel import Session, SQLModel, create_engine, text

db_url = settings.DATABASE_URL
# Handle external postgres URLs (Render / Heroku / Supabase)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def init_db() -> None:
    # Import all models so SQLModel metadata is registered
    import backend.app.models.chat  # noqa: F401
    import backend.app.models.dataset  # noqa: F401
    import backend.app.models.run  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def ping_db() -> bool:
    """Checks database availability for /ready probe."""
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return True
    except Exception:
        return False
