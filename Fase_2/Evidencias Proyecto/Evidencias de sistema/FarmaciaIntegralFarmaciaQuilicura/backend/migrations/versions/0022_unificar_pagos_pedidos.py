"""Unificar pagos, preparación de pedidos y auditoría."""

from alembic import op

revision = "0022_unificar_pagos_pedidos"
down_revision = (
    "0020_pagos_mercadopago",
    "0021_auditoria_actor_historico",
)
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "ck_pedido_estado",
        "pedido_online",
        type_="check",
    )
    op.create_check_constraint(
        "ck_pedido_estado",
        "pedido_online",
        "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO',"
        "'REVISION_PAGO','EN_PREPARACION','LISTO_PARA_RETIRO')",
    )


def downgrade():
    # Ambas ramas predecesoras conservan los seis estados.
    # Separar las cabeceras no requiere modificar datos ni la restricción.
    pass