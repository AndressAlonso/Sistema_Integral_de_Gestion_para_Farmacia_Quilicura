"""Retiro atómico y notificaciones de pedidos sin caducidad del QR."""
import sqlalchemy as sa
from alembic import op

revision = "0023_retiro_notificaciones"
down_revision = "0022_unificar_pagos_pedidos"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online", "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO','REVISION_PAGO','EN_PREPARACION','LISTO_PARA_RETIRO','RETIRADO')")
    op.create_table("retiro_pedido",
        sa.Column("pedido_id", sa.Uuid(), sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("codigo", sa.String(64), nullable=False),
        sa.Column("codigo_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("listo_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retirado_en", sa.DateTime(timezone=True)),
        sa.Column("usuario_id", sa.Uuid()), sa.Column("usuario_nombre", sa.String(150)))
    op.create_table("correo_pedido",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pedido_id", sa.Uuid(), sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False), sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("proximo_intento", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("enviado_en", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("pedido_id", "tipo", name="uq_correo_pedido_tipo"))
    op.create_index("ix_correo_pedido_pedido_id", "correo_pedido", ["pedido_id"])


def downgrade():
    # Conservar entregas históricas: no convertir silenciosamente un retiro en pendiente.
    if op.get_bind().execute(sa.text("SELECT 1 FROM pedido_online WHERE estado='RETIRADO' LIMIT 1")).first():
        raise RuntimeError("No se puede revertir mientras existan pedidos retirados.")
    op.drop_table("correo_pedido")
    op.drop_table("retiro_pedido")
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online", "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO','REVISION_PAGO','EN_PREPARACION','LISTO_PARA_RETIRO')")
