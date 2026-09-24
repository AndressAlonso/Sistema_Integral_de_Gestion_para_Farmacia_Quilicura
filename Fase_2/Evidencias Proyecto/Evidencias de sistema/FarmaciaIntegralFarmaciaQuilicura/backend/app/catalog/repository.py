"""E2-H1: categorías del catálogo global, sin stock por sucursal."""
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Categoria


class PostgresCatalogRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def list_categories(self) -> list[dict]:
        with self.session_factory() as db:
            rows = db.scalars(select(Categoria).order_by(Categoria.nombre, Categoria.id))
            return [{"id": row.id, "name": row.nombre} for row in rows]

    def create_category(self, name: str) -> dict:
        with self.session_factory.begin() as db:
            row = Categoria(nombre=name)
            db.add(row)
            db.flush()
            result = {"id": row.id, "name": row.nombre}
        return result
