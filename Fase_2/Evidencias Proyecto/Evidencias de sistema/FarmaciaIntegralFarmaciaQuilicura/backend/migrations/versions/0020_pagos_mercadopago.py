"""E7-H2: pagos verificados y ventas online sin caja ni salida física."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020_pagos_mercadopago"
down_revision = "0019_checkout_mercadopago"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint(
        "ck_pedido_estado",
        "pedido_online",
        "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO','REVISION_PAGO')",
    )
    op.add_column(
        "venta", sa.Column("pedido_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_venta_pedido",
        "venta",
        "pedido_online",
        ["pedido_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_venta_pedido", "venta", ["pedido_id"])
    op.alter_column("venta", "sesion_caja_id", nullable=True)
    op.alter_column("venta", "usuario_id", nullable=True)
    for column in ("subtotal", "descuento", "total"):
        op.alter_column(
            "venta", column, type_=sa.Numeric(18, 2), existing_type=sa.Numeric(14, 2)
        )
    op.alter_column(
        "venta_detalle",
        "total",
        type_=sa.Numeric(18, 2),
        existing_type=sa.Numeric(14, 2),
    )
    op.alter_column(
        "venta_detalle", "nombre", type_=sa.String(200), existing_type=sa.String(150)
    )
    op.drop_constraint("ck_venta_pago", "venta", type_="check")
    op.create_check_constraint(
        "ck_venta_pago",
        "venta",
        "medio_pago IN ('EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA','MERCADOPAGO')",
    )
    op.create_check_constraint(
        "ck_venta_canal",
        "venta",
        "(pedido_id IS NULL AND sesion_caja_id IS NOT NULL AND usuario_id IS NOT NULL AND medio_pago <> 'MERCADOPAGO') OR (pedido_id IS NOT NULL AND sesion_caja_id IS NULL AND usuario_id IS NULL AND medio_pago = 'MERCADOPAGO')",
    )
    op.create_table(
        "pago_mercadopago",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column(
            "pedido_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column(
            "proveedor_actualizado_en", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "procesado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revision_motivo", sa.String(100), nullable=True),
        sa.CheckConstraint("total > 0 AND moneda = 'CLP'", name="ck_pago_mp_importe"),
    )
    op.create_index("ix_pago_mercadopago_pedido_id", "pago_mercadopago", ["pedido_id"])


def downgrade():
    # Una reversión estructural no puede borrar pagos ni ventas existentes.
    bind = op.get_bind()
    if bind.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM pago_mercadopago) OR EXISTS(SELECT 1 FROM venta WHERE pedido_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("No se puede revertir: existen pagos o ventas online.")
    op.drop_table("pago_mercadopago")
    op.drop_constraint("ck_venta_canal", "venta", type_="check")
    op.drop_constraint("ck_venta_pago", "venta", type_="check")
    op.create_check_constraint(
        "ck_venta_pago",
        "venta",
        "medio_pago IN ('EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA')",
    )
    op.drop_constraint("uq_venta_pedido", "venta", type_="unique")
    op.drop_constraint("fk_venta_pedido", "venta", type_="foreignkey")
    op.drop_column("venta", "pedido_id")
    op.alter_column("venta", "sesion_caja_id", nullable=False)
    op.alter_column("venta", "usuario_id", nullable=False)
    for column in ("subtotal", "descuento", "total"):
        op.alter_column(
            "venta", column, type_=sa.Numeric(14, 2), existing_type=sa.Numeric(18, 2)
        )
    op.alter_column(
        "venta_detalle",
        "total",
        type_=sa.Numeric(14, 2),
        existing_type=sa.Numeric(18, 2),
    )
    op.alter_column(
        "venta_detalle", "nombre", type_=sa.String(150), existing_type=sa.String(200)
    )
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint(
        "ck_pedido_estado", "pedido_online", "estado IN ('PENDIENTE_PAGO','CANCELADO')"
    )
