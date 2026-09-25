"""Persistencia de categorias y productos en PostgreSQL."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.catalog.schemas import (
    CategoryResponse,
    CreateProduct,
    ProductResponse,
)
from app.models import Categoria, CodigoBarra, Producto


class PostgresCatalogRepository:
    def __init__(self, factory: sessionmaker[Session]):
        self.factory = factory

    def list_categories(self) -> list[CategoryResponse]:
        with self.factory() as session:
            categories = session.scalars(
                select(Categoria).order_by(Categoria.nombre, Categoria.id)
            ).all()

            return [
                CategoryResponse(id=category.id, name=category.nombre)
                for category in categories
            ]

    def create_category(self, name: str) -> CategoryResponse:
        with self.factory() as session:
            with session.begin():
                category = Categoria(nombre=name)
                session.add(category)
                session.flush()

                result = CategoryResponse(
                    id=category.id,
                    name=category.nombre,
                )

            return result

    @staticmethod
    def _product_response(product: Producto) -> ProductResponse:
        return ProductResponse(
            id=product.id,
            sku=product.sku,
            name=product.nombre,
            description=product.descripcion,
            category_id=product.categoria_id,
            price=product.precio_actual,
            requires_prescription=product.requiere_receta,
            is_active=product.activo,
            published_online=product.publicado_online,
            barcodes=sorted(
                barcode.valor for barcode in product.codigos_barra
            ),
        )

    def list_products(self) -> list[ProductResponse]:
        with self.factory() as session:
            products = session.scalars(
                select(Producto)
                .options(selectinload(Producto.codigos_barra))
                .order_by(Producto.nombre, Producto.id)
            ).all()

            return [
                self._product_response(product)
                for product in products
            ]

    def create_product(self, data: CreateProduct) -> ProductResponse:
        with self.factory() as session:
            try:
                with session.begin():
                    category = session.get(Categoria, data.category_id)
                    if category is None:
                        raise HTTPException(
                            status_code=422,
                            detail="La categoria seleccionada no existe.",
                        )

                    existing_sku = session.scalar(
                        select(Producto.id).where(
                            Producto.sku == data.sku
                        )
                    )
                    if existing_sku is not None:
                        raise HTTPException(
                            status_code=409,
                            detail="Ya existe un producto con ese SKU.",
                        )

                    if data.barcodes:
                        existing_barcode = session.scalar(
                            select(CodigoBarra.valor)
                            .where(CodigoBarra.valor.in_(data.barcodes))
                            .limit(1)
                        )
                        if existing_barcode is not None:
                            raise HTTPException(
                                status_code=409,
                                detail=(
                                    "Uno de los codigos de barras "
                                    "ya esta registrado."
                                ),
                            )

                    product = Producto(
                        sku=data.sku,
                        nombre=data.name,
                        descripcion=data.description,
                        categoria_id=data.category_id,
                        precio_actual=data.price,
                        requiere_receta=data.requires_prescription,
                        activo=data.is_active,
                        publicado_online=data.published_online,
                        codigos_barra=[
                            CodigoBarra(valor=value)
                            for value in data.barcodes
                        ],
                    )

                    session.add(product)
                    session.flush()
                    result = self._product_response(product)

                return result

            except IntegrityError as exc:
                # El contexto de la transaccion ya hizo rollback.
                # Estas restricciones tambien protegen ante solicitudes
                # simultaneas que superen las comprobaciones anteriores.
                diagnostic = getattr(exc.orig, "diag", None)
                constraint = getattr(
                    diagnostic, "constraint_name", None
                )

                if constraint == "uq_producto_sku":
                    raise HTTPException(
                        status_code=409,
                        detail="Ya existe un producto con ese SKU.",
                    ) from exc

                if constraint == "uq_codigo_barra_valor":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Uno de los codigos de barras "
                            "ya esta registrado."
                        ),
                    ) from exc

                raise