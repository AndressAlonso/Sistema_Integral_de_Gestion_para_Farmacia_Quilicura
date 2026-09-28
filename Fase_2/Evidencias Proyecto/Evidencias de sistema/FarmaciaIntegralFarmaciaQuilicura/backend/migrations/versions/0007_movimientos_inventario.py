"""E3-H4: kardex de movimientos de inventario."""

import sqlalchemy as sa
from alembic import op


revision = "0007_movimientos_inventario"
down_revision = "0006_stock_minimo"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "movimiento_inventario",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "inventario_sucursal_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "tipo",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "cantidad_fisica",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "cantidad_reservada",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "stock_fisico_anterior",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "stock_fisico_resultante",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "stock_reservado_anterior",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "stock_reservado_resultante",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "motivo",
            sa.String(length=250),
            nullable=False,
        ),
        sa.Column(
            "referencia_tipo",
            sa.String(length=60),
            nullable=True,
        ),
        sa.Column(
            "referencia_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "btrim(tipo) <> '' "
            "AND tipo = btrim(tipo)",
            name="ck_movimiento_inventario_tipo",
        ),
        sa.CheckConstraint(
            "cantidad_fisica <> 0 "
            "OR cantidad_reservada <> 0",
            name="ck_movimiento_inventario_cambio",
        ),
        sa.CheckConstraint(
            "stock_fisico_anterior >= 0",
            name="ck_movimiento_stock_fisico_anterior",
        ),
        sa.CheckConstraint(
            "stock_fisico_resultante >= 0",
            name="ck_movimiento_stock_fisico_resultante",
        ),
        sa.CheckConstraint(
            "stock_reservado_anterior >= 0",
            name="ck_movimiento_stock_reservado_anterior",
        ),
        sa.CheckConstraint(
            "stock_reservado_resultante >= 0",
            name="ck_movimiento_stock_reservado_resultante",
        ),
        sa.CheckConstraint(
            "stock_reservado_anterior "
            "<= stock_fisico_anterior",
            name="ck_movimiento_stock_anterior_consistente",
        ),
        sa.CheckConstraint(
            "stock_reservado_resultante "
            "<= stock_fisico_resultante",
            name="ck_movimiento_stock_resultante_consistente",
        ),
        sa.CheckConstraint(
            "stock_fisico_resultante = "
            "stock_fisico_anterior + cantidad_fisica",
            name="ck_movimiento_cambio_fisico",
        ),
        sa.CheckConstraint(
            "stock_reservado_resultante = "
            "stock_reservado_anterior + cantidad_reservada",
            name="ck_movimiento_cambio_reservado",
        ),
        sa.CheckConstraint(
            "btrim(motivo) <> ''",
            name="ck_movimiento_inventario_motivo",
        ),
        sa.ForeignKeyConstraint(
            ["inventario_sucursal_id"],
            ["inventario_sucursal.id"],
            name="fk_movimiento_inventario_inventario",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario_interno.id"],
            name="fk_movimiento_inventario_usuario",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_movimiento_inventario",
        ),
    )

    op.create_index(
        "ix_movimiento_inventario_inventario_sucursal_id",
        "movimiento_inventario",
        ["inventario_sucursal_id"],
        unique=False,
    )

    op.create_index(
        "ix_movimiento_inventario_usuario_id",
        "movimiento_inventario",
        ["usuario_id"],
        unique=False,
    )

    op.create_index(
        "ix_movimiento_inventario_tipo",
        "movimiento_inventario",
        ["tipo"],
        unique=False,
    )

    op.create_index(
        "ix_movimiento_inventario_creado_en",
        "movimiento_inventario",
        ["creado_en"],
        unique=False,
    )

    op.create_index(
        "ix_movimiento_inventario_consulta",
        "movimiento_inventario",
        [
            "inventario_sucursal_id",
            "creado_en",
        ],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_movimiento_inventario_consulta",
        table_name="movimiento_inventario",
    )

    op.drop_index(
        "ix_movimiento_inventario_creado_en",
        table_name="movimiento_inventario",
    )

    op.drop_index(
        "ix_movimiento_inventario_tipo",
        table_name="movimiento_inventario",
    )

    op.drop_index(
        "ix_movimiento_inventario_usuario_id",
        table_name="movimiento_inventario",
    )

    op.drop_index(
        "ix_movimiento_inventario_inventario_sucursal_id",
        table_name="movimiento_inventario",
    )

    op.drop_table(
        "movimiento_inventario",
    )