"""E4-H1/H2/H3: solicitudes, reserva por lote, despacho y recepción completa."""

import sqlalchemy as sa
from alembic import op

revision = "0009_transferencias"
down_revision = "0008_recepcion_mercaderia"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transferencia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("solicitud_hash", sa.String(64), nullable=False),
        sa.Column("origen_id", sa.Uuid(), sa.ForeignKey("sucursal.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destino_id", sa.Uuid(), sa.ForeignKey("sucursal.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        *[sa.Column(name, sa.Uuid(), sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"), nullable=name != "solicitante_id")
          for name in ("solicitante_id", "autorizador_id", "despachador_id", "receptor_id", "rechazada_por_id")],
        sa.Column("solicitada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        *[sa.Column(name, sa.DateTime(timezone=True), nullable=True)
          for name in ("autorizada_en", "despachada_en", "recibida_en", "rechazada_en")],
        sa.Column("motivo_rechazo", sa.String(250), nullable=True),
        sa.CheckConstraint("origen_id <> destino_id", name="ck_transferencia_sucursales"),
        sa.CheckConstraint("estado IN ('SOLICITADA','AUTORIZADA','EN_TRANSITO','RECIBIDA','RECHAZADA')", name="ck_transferencia_estado"),
    )
    for column in ("origen_id", "destino_id", "estado", "solicitada_en"):
        op.create_index(f"ix_transferencia_{column}", "transferencia", [column])
    op.create_table(
        "transferencia_detalle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transferencia_id", sa.Uuid(), sa.ForeignKey("transferencia.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("producto_id", sa.Uuid(), sa.ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.UniqueConstraint("transferencia_id", "producto_id", name="uq_transferencia_producto"),
        sa.CheckConstraint("cantidad > 0", name="ck_transferencia_detalle_cantidad"),
    )
    for column in ("transferencia_id", "producto_id"):
        op.create_index(f"ix_transferencia_detalle_{column}", "transferencia_detalle", [column])
    op.create_table(
        "transferencia_lote",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("detalle_id", sa.Uuid(), sa.ForeignKey("transferencia_detalle.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lote_origen_id", sa.Uuid(), sa.ForeignKey("lote_inventario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lote_destino_id", sa.Uuid(), sa.ForeignKey("lote_inventario.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.UniqueConstraint("detalle_id", "lote_origen_id", name="uq_transferencia_detalle_lote"),
        sa.CheckConstraint("cantidad > 0", name="ck_transferencia_lote_cantidad"),
    )
    for column in ("detalle_id", "lote_origen_id", "lote_destino_id"):
        op.create_index(f"ix_transferencia_lote_{column}", "transferencia_lote", [column])


def downgrade():
    op.drop_table("transferencia_lote")
    op.drop_table("transferencia_detalle")
    op.drop_table("transferencia")
