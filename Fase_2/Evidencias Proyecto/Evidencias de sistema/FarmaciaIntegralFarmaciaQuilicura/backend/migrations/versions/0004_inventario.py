"""E3-H1: inventario de productos por sucursal."""

import sqlalchemy as sa
from alembic import op


revision = "0004_inventario"
down_revision = "0003_producto_imagen"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventario_sucursal",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
        ),
        sa.Column(
            "producto_id",
            sa.Uuid(),
            sa.ForeignKey(
                "producto.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "sucursal_id",
            sa.Uuid(),
            sa.ForeignKey(
                "sucursal.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "stock_fisico",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "stock_reservado",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint(
            "producto_id",
            "sucursal_id",
            name="uq_inventario_producto_sucursal",
        ),
        sa.CheckConstraint(
            "stock_fisico >= 0",
            name="ck_inventario_stock_fisico",
        ),
        sa.CheckConstraint(
            "stock_reservado >= 0",
            name="ck_inventario_stock_reservado",
        ),
        sa.CheckConstraint(
            "stock_reservado <= stock_fisico",
            name="ck_inventario_stock_reservado_fisico",
        ),
    )

    op.create_index(
        "ix_inventario_sucursal_producto_id",
        "inventario_sucursal",
        ["producto_id"],
    )

    op.create_index(
        "ix_inventario_sucursal_sucursal_id",
        "inventario_sucursal",
        ["sucursal_id"],
    )


def downgrade():
    op.drop_index(
        "ix_inventario_sucursal_sucursal_id",
        table_name="inventario_sucursal",
    )

    op.drop_index(
        "ix_inventario_sucursal_producto_id",
        table_name="inventario_sucursal",
    )

    op.drop_table("inventario_sucursal")