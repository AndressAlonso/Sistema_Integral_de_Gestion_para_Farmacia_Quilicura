from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import database_url


def create_database_engine():
    return create_engine(database_url(), pool_pre_ping=True, hide_parameters=True)


def create_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
