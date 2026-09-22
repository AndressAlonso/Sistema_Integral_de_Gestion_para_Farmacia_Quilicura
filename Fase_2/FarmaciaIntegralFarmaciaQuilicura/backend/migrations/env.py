from alembic import context

from app.config import database_url
from app.db import create_database_engine
from app.models import Base


def run_migrations():
    if context.is_offline_mode():
        context.configure(url=database_url(), target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = context.config.attributes.get("connection")
    if engine is not None:
        context.configure(connection=engine, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_database_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
