"""E3-H3: stock mínimo por producto y sucursal."""

import sqlalchemy as sa
from alembic import op


revision = "0006_stock_minimo"
down_revision = "0005_lotes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "inventario_sucursal",
        sa.Column(
            "stock_minimo",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_check_constraint(
        "ck_inventario_stock_minimo",
        "inventario_sucursal",
        "stock_minimo >= 0",
    )


def downgrade():
    op.drop_constraint(
        "ck_inventario_stock_minimo",
        "inventario_sucursal",
        type_="check",
    )

    op.drop_column(
        "inventario_sucursal",
        "stock_minimo",
    )
