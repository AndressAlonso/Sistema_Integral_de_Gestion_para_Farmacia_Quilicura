"""Código numérico alternativo sin modificar los QR existentes."""
import secrets

import sqlalchemy as sa
from alembic import op

revision = "0024_codigo_manual_retiro"
down_revision = "0023_retiro_notificaciones"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("retiro_pedido", sa.Column("codigo_manual", sa.String(16)))
    db = op.get_bind()
    used = set()
    for identity in db.execute(sa.text("SELECT pedido_id FROM retiro_pedido")).scalars().all():
        while (code := f"{secrets.randbelow(10**16):016d}") in used:
            pass
        used.add(code)
        db.execute(sa.text("UPDATE retiro_pedido SET codigo_manual=:code WHERE pedido_id=:identity"), {"code": code, "identity": identity})
    op.alter_column("retiro_pedido", "codigo_manual", nullable=False)
    op.create_unique_constraint("uq_retiro_codigo_manual", "retiro_pedido", ["codigo_manual"])
    op.create_check_constraint("ck_retiro_codigo_manual", "retiro_pedido", "codigo_manual ~ '^[0-9]{16}$'")


def downgrade():
    op.drop_constraint("ck_retiro_codigo_manual", "retiro_pedido", type_="check")
    op.drop_constraint("uq_retiro_codigo_manual", "retiro_pedido", type_="unique")
    op.drop_column("retiro_pedido", "codigo_manual")
