from backend.app.config import settings
from sqlmodel import Session, SQLModel, create_engine

# SQLite connection args
connect_args = {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG, connect_args=connect_args)


def init_db() -> None:
    # Import all models so SQLModel metadata is registered
    import backend.app.models.chat  # noqa: F401
    import backend.app.models.dataset  # noqa: F401
    import backend.app.models.run  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
