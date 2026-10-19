"""E7-H1: pedidos online y reservas por lote, sin ventas ni pagos."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018_pedidos_reservas"
down_revision = "0017_promociones"
branch_labels = None
depends_on = None


def upgrade():
    uid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "pedido_online",
        sa.Column("id", uid, primary_key=True),
        sa.Column("solicitud_hash", sa.String(64), nullable=False),
        sa.Column("clave_hash", sa.String(64), nullable=False),
        sa.Column("cliente_id", uid, sa.ForeignKey("cliente.id", ondelete="RESTRICT")),
        sa.Column(
            "sucursal_id",
            uid,
            sa.ForeignKey("sucursal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE_PAGO','CANCELADO')", name="ck_pedido_estado"
        ),
        sa.CheckConstraint("total >= 0", name="ck_pedido_total"),
        sa.CheckConstraint(
            "btrim(nombre) <> '' AND btrim(correo) <> ''", name="ck_pedido_contacto"
        ),
    )
    for column in ["cliente_id", "sucursal_id", "estado"]:
        op.create_index("ix_pedido_online_" + column, "pedido_online", [column])
    op.create_table(
        "pedido_detalle",
        sa.Column("id", uid, primary_key=True),
        sa.Column(
            "pedido_id",
            uid,
            sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            uid,
            sa.ForeignKey("producto.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(14, 2), nullable=False),
        sa.Column("precio_base", sa.Numeric(14, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("promocion", sa.String(150)),
        sa.UniqueConstraint("pedido_id", "producto_id", name="uq_pedido_producto"),
        sa.CheckConstraint(
            "cantidad > 0 AND precio_unitario >= 0 AND subtotal >= 0",
            name="ck_pedido_detalle_valores",
        ),
    )
    op.create_index("ix_pedido_detalle_pedido_id", "pedido_detalle", ["pedido_id"])
    op.create_table(
        "reserva_pedido",
        sa.Column("id", uid, primary_key=True),
        sa.Column(
            "pedido_id",
            uid,
            sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "detalle_id",
            uid,
            sa.ForeignKey("pedido_detalle.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "lote_id",
            uid,
            sa.ForeignKey("lote_inventario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("detalle_id", "lote_id", name="uq_reserva_pedido_lote"),
        sa.CheckConstraint("cantidad > 0", name="ck_reserva_pedido_cantidad"),
    )
    for column in ["pedido_id", "lote_id", "activa"]:
        op.create_index("ix_reserva_pedido_" + column, "reserva_pedido", [column])


def downgrade():
    op.drop_table("reserva_pedido")
    op.drop_table("pedido_detalle")
    op.drop_table("pedido_online")
