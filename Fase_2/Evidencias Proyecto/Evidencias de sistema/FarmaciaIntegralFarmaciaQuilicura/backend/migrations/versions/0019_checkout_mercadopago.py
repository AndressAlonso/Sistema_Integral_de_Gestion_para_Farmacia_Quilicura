"""E7-H2: persistencia de preferencias; no registra pagos ni ventas."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_checkout_mercadopago"
down_revision = "0018_pedidos_reservas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "checkout_mercadopago",
        sa.Column(
            "pedido_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pedido_online.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("preferencia_id", sa.String(200), nullable=True),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("preferencia_id"),
        sa.CheckConstraint(
            "estado IN ('CREANDO','LISTO','INCIERTO')", name="ck_checkout_mp_estado"
        ),
        sa.CheckConstraint("total > 0 AND moneda = 'CLP'", name="ck_checkout_mp_importe"),
        sa.CheckConstraint("vence_en > creado_en", name="ck_checkout_mp_plazo"),
        sa.CheckConstraint(
            "(estado = 'LISTO' AND preferencia_id IS NOT NULL "
            "AND btrim(preferencia_id) <> '' AND checkout_url IS NOT NULL "
            "AND btrim(checkout_url) <> '') OR "
            "(estado IN ('CREANDO','INCIERTO') AND preferencia_id IS NULL "
            "AND checkout_url IS NULL)",
            name="ck_checkout_mp_enlace",
        ),
    )


def downgrade():
    op.drop_table("checkout_mercadopago")
