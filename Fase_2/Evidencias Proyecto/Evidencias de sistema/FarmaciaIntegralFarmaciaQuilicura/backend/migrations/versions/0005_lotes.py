"""E3-H2: lotes y fechas de vencimiento."""

import sqlalchemy as sa
from alembic import op


revision = "0005_lotes"
down_revision = "0004_inventario"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lote_inventario",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
        ),
        sa.Column(
            "inventario_sucursal_id",
            sa.Uuid(),
            sa.ForeignKey(
                "inventario_sucursal.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "numero_lote",
            sa.String(80),
            nullable=False,
        ),
        sa.Column(
            "fecha_vencimiento",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "cantidad",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "inventario_sucursal_id",
            "numero_lote",
            name="uq_lote_inventario_numero",
        ),
        sa.CheckConstraint(
            "btrim(numero_lote) <> '' "
            "AND numero_lote = btrim(numero_lote)",
            name="ck_lote_inventario_numero",
        ),
        sa.CheckConstraint(
            "cantidad >= 0",
            name="ck_lote_inventario_cantidad",
        ),
    )

    op.create_index(
        "ix_lote_inventario_inventario_sucursal_id",
        "lote_inventario",
        ["inventario_sucursal_id"],
    )

    op.create_index(
        "ix_lote_inventario_fecha_vencimiento",
        "lote_inventario",
        ["fecha_vencimiento"],
    )


def downgrade():
    op.drop_index(
        "ix_lote_inventario_fecha_vencimiento",
        table_name="lote_inventario",
    )

    op.drop_index(
        "ix_lote_inventario_inventario_sucursal_id",
        table_name="lote_inventario",
    )

    op.drop_table("lote_inventario")