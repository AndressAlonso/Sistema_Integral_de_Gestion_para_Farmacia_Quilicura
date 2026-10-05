"""E2-H1: catálogo global según el diagrama de clases final v2.

Una categoría por producto; cero o varios códigos por producto.
No modifica las tablas de E1 ni incorpora stock, promociones o auditoría.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_catalogo"
down_revision = "0001_acceso"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_categoria_nombre"),
    )
    op.create_table(
        "producto",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("publicado_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requiere_receta", sa.Boolean(), nullable=False),
        sa.Column("precio_actual", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "categoria_id", sa.Uuid(),
            sa.ForeignKey("categoria.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.UniqueConstraint("sku", name="uq_producto_sku"),
        sa.CheckConstraint("btrim(sku) <> '' AND sku = btrim(sku)", name="ck_producto_sku"),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_producto_nombre"),
        sa.CheckConstraint(
            "precio_actual >= 0 AND precio_actual < 1000000000000",
            name="ck_producto_precio_actual",
        ),
    )
    op.create_index("ix_producto_categoria_id", "producto", ["categoria_id"])
    op.create_table(
        "codigo_barra",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("valor", sa.String(128), nullable=False),
        sa.Column(
            "producto_id", sa.Uuid(),
            sa.ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.UniqueConstraint("valor", name="uq_codigo_barra_valor"),
        sa.CheckConstraint(
            "btrim(valor) <> '' AND valor = btrim(valor)", name="ck_codigo_barra_valor",
        ),
    )
    op.create_index("ix_codigo_barra_producto_id", "codigo_barra", ["producto_id"])


def downgrade():
    op.drop_index("ix_codigo_barra_producto_id", table_name="codigo_barra")
    op.drop_table("codigo_barra")
    op.drop_index("ix_producto_categoria_id", table_name="producto")
    op.drop_table("producto")
    op.drop_table("categoria")
