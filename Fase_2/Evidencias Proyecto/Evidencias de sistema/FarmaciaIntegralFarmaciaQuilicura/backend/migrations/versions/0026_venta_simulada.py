"""E7: venta de prueba explícita para el flujo local completo."""
from alembic import op

revision = "0026_venta_simulada"
down_revision = "0025_motivo_ajuste"
branch_labels = None
depends_on = None


def constraints(simulated):
    methods = "'MERCADOPAGO','SIMULADO'" if simulated else "'MERCADOPAGO'"
    op.create_check_constraint("ck_venta_pago", "venta", f"medio_pago IN ('EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA',{methods})")
    op.create_check_constraint("ck_venta_canal", "venta", f"(pedido_id IS NULL AND sesion_caja_id IS NOT NULL AND usuario_id IS NOT NULL AND medio_pago NOT IN ({methods})) OR (pedido_id IS NOT NULL AND sesion_caja_id IS NULL AND usuario_id IS NULL AND medio_pago IN ({methods}))")


def upgrade():
    op.drop_constraint("ck_venta_pago", "venta", type_="check")
    op.drop_constraint("ck_venta_canal", "venta", type_="check")
    constraints(True)


def downgrade():
    # Rechaza revertir mientras existan ventas simuladas; no borra datos.
    op.drop_constraint("ck_venta_pago", "venta", type_="check")
    op.drop_constraint("ck_venta_canal", "venta", type_="check")
    constraints(False)
