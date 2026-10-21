"""E7-H3: vincular traslados con reservas existentes y habilitar pedido pagado."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_transferencias_pedido"
down_revision = "0018_pedidos_reservas"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online",
                               "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO')")
    op.add_column("transferencia", sa.Column("pedido_id", postgresql.UUID(), nullable=True))
    op.create_foreign_key("fk_transferencia_pedido", "transferencia", "pedido_online",
                          ["pedido_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_transferencia_pedido_origen", "transferencia", ["pedido_id", "origen_id"])
    op.alter_column("transferencia", "solicitante_id", nullable=True)
    op.create_check_constraint("ck_transferencia_solicitante", "transferencia",
                               "solicitante_id IS NOT NULL OR pedido_id IS NOT NULL")
    op.add_column("transferencia_lote", sa.Column("reserva_pedido_id", postgresql.UUID(), nullable=True))
    op.create_foreign_key("fk_transferencia_lote_reserva", "transferencia_lote", "reserva_pedido",
                          ["reserva_pedido_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_transferencia_lote_reserva", "transferencia_lote", ["reserva_pedido_id"])


def downgrade():
    # No destruir trazabilidad ni convertir pedidos pagados de forma silenciosa.
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM transferencia WHERE pedido_id IS NOT NULL)
        OR EXISTS (SELECT 1 FROM pedido_online WHERE estado='PAGADO') THEN
        RAISE EXCEPTION 'No se puede revertir con pedidos pagados o transferencias online';
      END IF;
    END $$""")
    op.drop_constraint("uq_transferencia_lote_reserva", "transferencia_lote", type_="unique")
    op.drop_constraint("fk_transferencia_lote_reserva", "transferencia_lote", type_="foreignkey")
    op.drop_column("transferencia_lote", "reserva_pedido_id")
    op.drop_constraint("ck_transferencia_solicitante", "transferencia", type_="check")
    op.alter_column("transferencia", "solicitante_id", nullable=False)
    op.drop_constraint("uq_transferencia_pedido_origen", "transferencia", type_="unique")
    op.drop_constraint("fk_transferencia_pedido", "transferencia", type_="foreignkey")
    op.drop_column("transferencia", "pedido_id")
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online", "estado IN ('PENDIENTE_PAGO','CANCELADO')")

