from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file URL (shopsense.db will be saved in the root folder)
SQLALCHEMY_DATABASE_URL = "sqlite:///./shopsense.db"

# create_engine connects FastAPI to our SQLite database.
# check_same_thread=False is needed only for SQLite because FastAPI operates across multiple threads.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal is a factory that will generate database session instances for each request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class from which all SQLAlchemy database models (tables) will inherit.
Base = declarative_base()


# FastAPI Dependency: creates a fresh database session for every API request
# and ensures it is properly closed after the request completes.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
