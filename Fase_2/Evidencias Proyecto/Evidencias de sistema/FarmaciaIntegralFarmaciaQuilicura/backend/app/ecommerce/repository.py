from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.ecommerce.schemas import (
    Availability,
    PublicBranch,
    PublicCategory,
    PublicProduct,
)
from app.models import InventarioSucursal, Producto, Sucursal


class PublicCatalogRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def branches_query():
        return (
            select(Sucursal)
            .where(Sucursal.activa.is_(True))
            .order_by(Sucursal.nombre, Sucursal.id)
        )

    @staticmethod
    def products_query():
        return (
            select(Producto)
            .where(
                Producto.activo.is_(True),
                Producto.publicado_online.is_(True),
            )
            .options(selectinload(Producto.categoria))
            .order_by(Producto.nombre, Producto.id)
        )

    def branches(self):
        with self.factory() as db:
            return [
                PublicBranch(id=b.id, name=b.nombre, address=b.direccion_local)
                for b in db.scalars(self.branches_query())
            ]

    def products(
        self, q: str = "", branch_id: UUID | None = None, product_id: UUID | None = None
    ):
        with self.factory() as db:
            branches = list(db.scalars(self.branches_query()))
            if branch_id is not None:
                branches = [b for b in branches if b.id == branch_id]
                if not branches:
                    raise HTTPException(404, "La sucursal no está disponible.")
            query = self.products_query()
            if product_id is not None:
                query = query.where(Producto.id == product_id)
            if q:
                query = query.where(
                    or_(
                        Producto.nombre.icontains(q, autoescape=True),
                        Producto.descripcion.icontains(q, autoescape=True),
                    )
                )
            products = list(db.scalars(query))
            if product_id is not None and not products:
                raise HTTPException(404, "El producto no está disponible.")
            stocks = {
                (row.producto_id, row.sucursal_id): row.stock_disponible
                for row in db.scalars(
                    select(InventarioSucursal).where(
                        InventarioSucursal.producto_id.in_([p.id for p in products]),
                        InventarioSucursal.sucursal_id.in_([b.id for b in branches]),
                    )
                )
            }
            if any(value < 0 for value in stocks.values()):
                raise HTTPException(500, "No pudimos consultar la disponibilidad.")
            return [
                PublicProduct(
                    id=p.id,
                    name=p.nombre,
                    description=p.descripcion,
                    category=PublicCategory(id=p.categoria_id, name=p.categoria.nombre),
                    price=p.precio_actual,
                    requires_prescription=p.requiere_receta,
                    online_purchase_allowed=not p.requiere_receta,
                    image_url=f"/api/ecommerce/products/{p.id}/image?v={p.image_key}"
                    if p.image_key
                    else None,
                    availability=[
                        Availability(
                            branch_id=b.id,
                            branch_name=b.nombre,
                            available=stocks.get((p.id, b.id), 0),
                        )
                        for b in branches
                    ],
                )
                for p in products
            ]

    def image_key(self, product_id: UUID):
        with self.factory() as db:
            product = db.scalar(self.products_query().where(Producto.id == product_id))
            if product is None:
                raise HTTPException(404, "El producto no está disponible.")
            return product.image_key
