"""E4-H4: respaldo documental de entradas de mercadería y sus lotes."""

import sqlalchemy as sa
from alembic import op

revision = "0008_recepcion_mercaderia"
down_revision = "0007_movimientos_inventario"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recepcion_mercaderia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("solicitud_hash", sa.String(64), nullable=False),
        sa.Column("sucursal_id", sa.Uuid(), sa.ForeignKey("sucursal.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("proveedor", sa.String(150), nullable=False),
        sa.Column("tipo_documento", sa.String(20), nullable=False),
        sa.Column("numero_documento", sa.String(80), nullable=False),
        sa.Column("fecha_documento", sa.Date(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("btrim(proveedor) <> ''", name="ck_recepcion_proveedor"),
        sa.CheckConstraint("tipo_documento IN ('GUIA', 'FACTURA')", name="ck_recepcion_tipo_documento"),
        sa.CheckConstraint("btrim(numero_documento) <> ''", name="ck_recepcion_documento"),
    )
    for column in ("sucursal_id", "usuario_id"):
        op.create_index(f"ix_recepcion_mercaderia_{column}", "recepcion_mercaderia", [column])
    op.create_table(
        "recepcion_mercaderia_detalle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("recepcion_id", sa.Uuid(), sa.ForeignKey("recepcion_mercaderia.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lote_id", sa.Uuid(), sa.ForeignKey("lote_inventario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_recepcion_detalle_cantidad"),
        sa.UniqueConstraint("recepcion_id", "lote_id", name="uq_recepcion_detalle_lote"),
    )
    for column in ("recepcion_id", "lote_id"):
        op.create_index(f"ix_recepcion_mercaderia_detalle_{column}", "recepcion_mercaderia_detalle", [column])


def downgrade():
    op.drop_table("recepcion_mercaderia_detalle")
    op.drop_table("recepcion_mercaderia")
