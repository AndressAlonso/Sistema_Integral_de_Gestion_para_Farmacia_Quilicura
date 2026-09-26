"""E2-H1: altas y edicion atomica de productos y codigos."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.catalog.schemas import (
    CategoryResponse,
    CreateProduct,
    ProductResponse,
    UpdateProduct,
)
from app.models import Categoria, CodigoBarra, Producto


class PostgresCatalogRepository:
    def __init__(self, factory: sessionmaker[Session]):
        self.factory = factory

    @contextmanager
    def transaction(self):
        try:
            with self.factory.begin() as db:
                yield db
        except IntegrityError as exc:
            constraint = getattr(
                getattr(exc.orig, "diag", None), "constraint_name", None
            )
            if constraint in {"uq_producto_sku", "uq_codigo_barra_valor"}:
                raise HTTPException(
                    409, "El SKU o un codigo de barras ya esta registrado."
                ) from exc
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise HTTPException(
                    409,
                    "El registro esta relacionado con otros datos. Actualiza el listado.",
                ) from exc
            raise

    def list_categories(self):
        with self.factory() as db:
            return [
                CategoryResponse(id=c.id, name=c.nombre)
                for c in db.scalars(
                    select(Categoria).order_by(Categoria.nombre, Categoria.id)
                )
            ]

    def create_category(self, name: str):
        with self.transaction() as db:
            row = Categoria(nombre=name)
            db.add(row)
            db.flush()
            result = CategoryResponse(id=row.id, name=row.nombre)
        return result

    @staticmethod
    def response(row: Producto):
        return ProductResponse(
            id=row.id,
            sku=row.sku,
            name=row.nombre,
            description=row.descripcion,
            category_id=row.categoria_id,
            price=row.precio_actual,
            requires_prescription=row.requiere_receta,
            is_active=row.activo,
            published_online=row.publicado_online,
            barcodes=sorted(code.valor for code in row.codigos_barra),
            image_url=f"/api/products/{row.id}/image?v={row.image_key}"
            if row.image_key
            else None,
        )

    def list_products(self):
        with self.factory() as db:
            return [
                self.response(row)
                for row in db.scalars(
                    select(Producto)
                    .options(selectinload(Producto.codigos_barra))
                    .order_by(Producto.nombre, Producto.id)
                )
            ]

    def get_product(self, product_id: UUID):
        with self.factory() as db:
            return self.response(self.find(db, product_id))

    @staticmethod
    def find(db, product_id: UUID, lock: bool = False):
        query = select(Producto).where(Producto.id == product_id)
        if lock:
            query = query.with_for_update()
        row = db.scalar(query)
        if row is None:
            raise HTTPException(404, "El producto no existe.")
        return row

    @staticmethod
    def apply_fields(db, row, data: UpdateProduct):
        if db.get(Categoria, data.category_id) is None:
            raise HTTPException(422, "La categoria seleccionada no existe.")
        row.sku = data.sku
        row.nombre = data.name
        row.descripcion = data.description
        row.categoria_id = data.category_id
        row.requiere_receta = data.requires_prescription
        row.activo = data.is_active
        row.publicado_online = data.published_online

    @staticmethod
    def validate_codes(db, data, product_id=None):
        sku_query = select(Producto.id).where(Producto.sku == data.sku)
        codes_query = select(CodigoBarra.id).where(CodigoBarra.valor.in_(data.barcodes))
        if product_id is not None:
            sku_query = sku_query.where(Producto.id != product_id)
            codes_query = codes_query.where(CodigoBarra.producto_id != product_id)
        if db.scalar(sku_query.limit(1)) is not None:
            raise HTTPException(409, "Ya existe un producto con ese SKU.")
        if data.barcodes and db.scalar(codes_query.limit(1)) is not None:
            raise HTTPException(409, "Un codigo de barras ya esta registrado.")

    def create_product(self, data: CreateProduct):
        with self.transaction() as db:
            self.validate_codes(db, data)
            row = Producto(
                precio_actual=data.price,
                codigos_barra=[CodigoBarra(valor=code) for code in data.barcodes],
            )
            self.apply_fields(db, row, data)
            db.add(row)
            db.flush()
            result = self.response(row)
        return result

    def update_product(self, product_id: UUID, data: UpdateProduct):
        with self.transaction() as db:
            row = self.find(db, product_id, lock=True)
            self.validate_codes(db, data, product_id)
            self.apply_fields(db, row, data)
            existing = {code.valor: code for code in row.codigos_barra}
            desired = set(data.barcodes)
            for value, code in existing.items():
                if value not in desired:
                    db.delete(code)
            for value in desired - existing.keys():
                db.add(CodigoBarra(valor=value, producto_id=row.id))
            db.flush()
            db.expire(row, ["codigos_barra"])
            result = self.response(row)
        return result

    def set_image(self, product_id: UUID, key: str | None):
        with self.transaction() as db:
            row = self.find(db, product_id, lock=True)
            previous = row.image_key
            row.image_key = key
            db.flush()
            result = self.response(row)
        return result, previous

    def image_key(self, product_id: UUID):
        with self.factory() as db:
            return self.find(db, product_id).image_key
