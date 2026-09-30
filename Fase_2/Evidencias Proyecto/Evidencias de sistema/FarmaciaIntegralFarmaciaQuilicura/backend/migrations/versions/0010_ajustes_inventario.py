"""E4-H5: ajuste masivo trazable e idempotente por lote."""

import sqlalchemy as sa
from alembic import op

revision = "0010_ajustes_inventario"
down_revision = "0009_transferencias"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ajuste_inventario",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("solicitud_hash", sa.String(64), nullable=False),
        sa.Column(
            "sucursal_id",
            sa.Uuid(),
            sa.ForeignKey("sucursal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("motivo", sa.String(250), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("btrim(motivo) <> ''", name="ck_ajuste_motivo"),
    )
    for column in ("sucursal_id", "usuario_id"):
        op.create_index(f"ix_ajuste_inventario_{column}", "ajuste_inventario", [column])
    op.create_table(
        "ajuste_inventario_detalle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ajuste_id",
            sa.Uuid(),
            sa.ForeignKey("ajuste_inventario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "lote_id",
            sa.Uuid(),
            sa.ForeignKey("lote_inventario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad_anterior", sa.Integer(), nullable=False),
        sa.Column("cantidad_nueva", sa.Integer(), nullable=False),
        sa.UniqueConstraint("ajuste_id", "lote_id", name="uq_ajuste_lote"),
        sa.CheckConstraint(
            "cantidad_anterior >= 0 AND cantidad_nueva >= 0",
            name="ck_ajuste_cantidades",
        ),
        sa.CheckConstraint(
            "cantidad_anterior <> cantidad_nueva", name="ck_ajuste_cambio"
        ),
    )
    for column in ("ajuste_id", "lote_id"):
        op.create_index(
            f"ix_ajuste_inventario_detalle_{column}",
            "ajuste_inventario_detalle",
            [column],
        )


def downgrade():
    op.drop_table("ajuste_inventario_detalle")
    op.drop_table("ajuste_inventario")
