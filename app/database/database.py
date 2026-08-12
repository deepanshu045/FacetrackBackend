from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL, DATABASE_CONNECT_ARGS

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args=DATABASE_CONNECT_ARGS,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()