"""E7-H4: estados de preparación; historial en evento_auditoria existente."""
from alembic import op

revision = "0020_preparacion_pedidos"
down_revision = "0019_transferencias_pedido"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online",
        "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO','EN_PREPARACION','LISTO_PARA_RETIRO')")


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pedido_online WHERE estado IN ('EN_PREPARACION','LISTO_PARA_RETIRO')) THEN
        RAISE EXCEPTION 'No se puede revertir con pedidos en preparación o listos';
      END IF;
    END $$""")
    op.drop_constraint("ck_pedido_estado", "pedido_online", type_="check")
    op.create_check_constraint("ck_pedido_estado", "pedido_online",
        "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO')")
